import csv
import functools
import io
import json
import os
import secrets
import tempfile
import time
from pathlib import Path
import click
from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for, send_file, Response, stream_with_context
from werkzeug.security import generate_password_hash, check_password_hash
from openpyxl import Workbook
from .db import connect, get_db, init_db, now
from .ingest import ingest, KINDS
from .sources import SOURCES, probe, download_nse, download_data_gov, SourceError
from .analytics import directory, overview, query, research_score, DEFAULT_WEIGHTS


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_path = Path(app.instance_path)/'session.key'
    if not secret_path.exists():
        try:
            fd = os.open(secret_path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            with os.fdopen(fd,'w') as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or secret_path.read_text(),
                      DATABASE=os.getenv('DATABASE_PATH',str(Path(app.instance_path)/'intelligence.sqlite')),
                      MAX_CONTENT_LENGTH=100*1024*1024, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE')=='1',
                      SCORE_WEIGHTS=DEFAULT_WEIGHTS)
    if config:
        app.config.update(config)
    if os.getenv('SCORE_WEIGHTS_JSON'):
        app.config['SCORE_WEIGHTS'] = json.loads(os.environ['SCORE_WEIGHTS_JSON'])
    research_score({},app.config['SCORE_WEIGHTS'])
    with app.app_context():
        init_db(get_db())

    @app.teardown_appcontext
    def close_db(error):
        db = g.pop('db',None)
        if db is not None:
            db.close()

    @app.before_request
    def protect():
        g.user = None
        if session.get('user_id'):
            g.user = get_db().execute('SELECT id,username,role FROM users WHERE id=?',(session['user_id'],)).fetchone()
        if request.endpoint in ('static','login','health'):
            return
        if not g.user:
            if request.path.startswith('/api/'):
                return jsonify(error='Authentication required'),401
            return redirect(url_for('login'))
        if request.method in ('POST','PUT','PATCH','DELETE'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token','')
            if not secrets.compare_digest(str(token),session.get('csrf','')) or not token:
                abort(403,description='Invalid CSRF token')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(ValueError)
    def invalid(error):
        if request.path.startswith('/api/'):
            return jsonify(error=str(error)),400
        return render_template('error.html',message=str(error)),400

    @app.errorhandler(413)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(429)
    def http_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error=error.description),error.code
        return render_template('error.html',message=error.description),error.code

    @app.get('/healthz')
    def health():
        get_db().execute('SELECT 1').fetchone()
        return jsonify(status='ok')

    @app.route('/login',methods=['GET','POST'])
    def login():
        session.setdefault('csrf',secrets.token_hex(24))
        error = None
        if request.method == 'POST':
            if not secrets.compare_digest(request.form.get('csrf_token',''),session['csrf']):
                abort(403)
            if len(request.form.get('password',''))>1024 or len(request.form.get('username',''))>100:
                abort(403)
            ip = request.remote_addr or 'unknown'
            db = get_db()
            attempt = db.execute('SELECT * FROM login_attempts WHERE ip=?',(ip,)).fetchone()
            if attempt and attempt['failures']>=10 and time.time()-attempt['window_start']<900:
                abort(429,description='Too many login attempts. Retry after 15 minutes.')
            user = db.execute('SELECT * FROM users WHERE username=?',(request.form.get('username',''),)).fetchone()
            # Perform a password hash check for unknown users too.
            fallback = 'scrypt:32768:8:1$none$'+'0'*128
            valid = check_password_hash(user['password_hash'] if user else fallback,request.form.get('password',''))
            if user and valid:
                db.execute('DELETE FROM login_attempts WHERE ip=?',(ip,)); db.commit()
                session.clear(); session.update(user_id=user['id'],csrf=secrets.token_hex(24))
                return redirect(url_for('index'))
            start = attempt['window_start'] if attempt and time.time()-attempt['window_start']<900 else time.time()
            failures = attempt['failures']+1 if attempt and time.time()-attempt['window_start']<900 else 1
            db.execute('INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)',(ip,failures,start)); db.commit()
            error = 'Invalid username or password'
        return render_template('login.html',error=error)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    def admin():
        if g.user['role'] != 'admin':
            abort(403,description='Administrator access required')

    @app.get('/')
    def index():
        return render_template('index.html',sources=SOURCES)

    @app.get('/api/companies')
    def companies():
        return jsonify(directory(get_db(),request.args))

    @app.get('/api/overview')
    def stats():
        return jsonify(overview(get_db(),request.args))

    @app.get('/api/options')
    def options():
        db=get_db();status=request.args.get('status','');state=request.args.get('state','');district=request.args.get('city','')
        values={field:[row[0] for row in db.execute(f"SELECT DISTINCT {field} FROM companies WHERE {field} IS NOT NULL AND (?='' OR status=?) ORDER BY {field}",(status,status))] for field in ('state','industry','class','status','district','nic')}
        cities=[row[0] for row in db.execute("SELECT DISTINCT pin_district(postal_code,state) AS city FROM companies WHERE state=? AND (?='' OR status=?) ORDER BY city",(state,status,status))] if state else []
        values.update(city=[value for value in cities if value],city_unknown=int(None in cities))
        for field in ('roc','postal_code'):
            values[field]=[row[0] for row in db.execute(f"SELECT DISTINCT {field} FROM companies WHERE state=? AND {field} IS NOT NULL AND (?='' OR status=?) ORDER BY {field}",(state,status,status))] if state else []
        areas=[row[0] for row in db.execute("SELECT DISTINCT pin_area(postal_code,state) FROM companies WHERE state=? AND (?='' OR status=?) AND (?='' OR lower(COALESCE(pin_district(postal_code,state),'(Not identified)'))=lower(?)) ORDER BY 1",(state,status,status,district,district))] if state else []
        values.update(postal_city=[value for value in areas if value],postal_city_unknown=int(None in areas))
        return jsonify(values)

    @app.get('/api/company/<cin>')
    def profile(cin):
        db = get_db()
        rows = directory(db,{'q':cin,'reporting_type':request.args.get('reporting_type','standalone'),
                             'fy':request.args.get('fy','')})['rows']
        row = next((r for r in rows if r['cin']==cin),None)
        if not row:
            abort(404)
        result = {'company':row, 'score':research_score(row,app.config['SCORE_WEIGHTS'])}
        result['field_sources'] = [dict(r) for r in db.execute('SELECT field,source_id,as_of,import_id FROM field_sources WHERE kind=? AND record_key=? ORDER BY field',
                                                              ('companies',json.dumps([cin])))]
        for table in ('financials','historical_names','securities','directors','filings','company_history','financial_history'):
            result[table] = [dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE cin=? ORDER BY rowid DESC LIMIT 200',(cin,))]
        return jsonify(result)

    @app.get('/api/screen')
    def screen():
        args = request.args.to_dict() | {'listing':'unlisted'}
        result = directory(get_db(),args)
        for row in result['rows']:
            row['research_score'] = research_score(row,app.config['SCORE_WEIGHTS'])
        result['methodology'] = {'weights':app.config['SCORE_WEIGHTS'], 'notice':research_score({})['notice']}
        return jsonify(result)

    @app.get('/api/records/<kind>')
    def independent(kind):
        if kind not in ('securities','llps','msmes'):
            abort(404)
        db = get_db()
        page = max(1,int(request.args.get('page',1)))
        search = request.args.get('q','')
        # Literal substring search keeps this parameterized and avoids wildcard ambiguity.
        condition = ' WHERE instr(lower(name),lower(?))>0'
        count = db.execute(f'SELECT COUNT(*) FROM {kind}'+condition,(search,)).fetchone()[0]
        rows = db.execute(f'SELECT * FROM {kind}'+condition+' ORDER BY name LIMIT 50 OFFSET ?',(search,(page-1)*50))
        return jsonify(rows=[dict(r) for r in rows],total=count,page=page,per_page=50)

    @app.get('/api/sources')
    def source_status():
        return jsonify(sources=[dict(r)|{'note':SOURCES[r['id']]['note']} for r in get_db().execute('SELECT * FROM sources')],
                       imports=[dict(r) for r in get_db().execute('SELECT * FROM imports ORDER BY id DESC LIMIT 100')])

    @app.post('/api/sources/<source>/probe')
    def source_probe(source):
        admin()
        if source not in SOURCES:
            abort(404)
        status,message = probe(source)
        get_db().execute('UPDATE sources SET status=?,message=?,checked_at=? WHERE id=?',(status,message,now(),source))
        get_db().commit()
        return jsonify(status=status,message=message)

    @app.post('/api/import')
    def upload():
        admin()
        upload = request.files.get('file')
        if not upload or not upload.filename:
            raise ValueError('Select a CSV or XLSX dataset')
        extension = Path(upload.filename).suffix.lower()
        if extension not in ('.csv','.xlsx'):
            raise ValueError('Only CSV and XLSX files are supported')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/('upload'+extension)
            upload.save(path)
            result = ingest(get_db(),path,request.form.get('kind'),request.form.get('source'),request.form.get('as_of'))
        return jsonify(result), (422 if result['status']=='failed' else 200)

    @app.get('/api/template/<kind>')
    def template_csv(kind):
        from .ingest import REQUIRED
        if kind not in KINDS:
            abort(404)
        columns = [r['name'] for r in get_db().execute(f'PRAGMA table_info({kind})') if r['name'] not in ('source_id','as_of','import_id','updated_at')]
        output = io.StringIO(); csv.writer(output).writerow(columns)
        return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={kind}-template.csv'})

    def safe_cell(value):
        if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@','\t','\r')):
            return "'"+value
        return value

    @app.get('/api/export.<fmt>')
    def export(fmt):
        if fmt not in ('csv','xlsx'):
            abort(404)
        cursor,count = directory(get_db(),request.args,export=True)
        columns = [c[0] for c in cursor.description]
        if fmt == 'csv':
            database_path = app.config['DATABASE']
            export_args = request.args.to_dict()
            def generate():
                # A stream owns its connection: Flask may tear down the request DB before iteration.
                db = connect(database_path)
                try:
                    export_cursor,_ = directory(db,export_args,export=True)
                    output=io.StringIO(); writer=csv.writer(output)
                    writer.writerow(columns); yield output.getvalue(); output.seek(0); output.truncate(0)
                    for row in export_cursor:
                        writer.writerow([safe_cell(v) for v in row]); yield output.getvalue(); output.seek(0); output.truncate(0)
                finally:
                    db.close()
            return Response(stream_with_context(generate()),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=companies.csv'})
        if count>100000:
            raise ValueError('For more than 100,000 records use streaming CSV export or narrow filters')
        book=Workbook(write_only=True); sheet=book.create_sheet('Companies'); sheet.append(columns)
        for row in cursor:
            sheet.append([safe_cell(v) for v in row])
        output=io.BytesIO(); book.save(output); output.seek(0)
        return send_file(output,download_name='companies.xlsx',as_attachment=True)

    @app.cli.command('create-user')
    @click.argument('username')
    @click.option('--role',type=click.Choice(['admin','analyst']),default='admin')
    @click.password_option()
    def create_user(username,role,password):
        import re
        if not re.fullmatch(r'[A-Za-z0-9_.@-]{3,100}',username):
            raise click.ClickException('Username must be 3–100 letters, numbers or ._@- characters')
        if not 12<=len(password)<=1024:
            raise click.ClickException('Use a password between 12 and 1024 characters')
        db=get_db()
        if db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
            raise click.ClickException('User already exists')
        db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',
                   (username,generate_password_hash(password),role,now())); db.commit()
        click.echo('User created')

    @app.cli.command('import-data')
    @click.argument('path',type=click.Path(exists=True))
    @click.option('--kind',required=True,type=click.Choice(list(KINDS)))
    @click.option('--source',required=True,type=click.Choice(list(SOURCES)))
    @click.option('--as-of',required=True)
    def import_data(path,kind,source,as_of):
        result=ingest(get_db(),path,kind,source,as_of)
        click.echo(json.dumps(result,indent=2))
        if result['status'] in ('failed','partial'):
            raise click.ClickException('Import has rejected records; inspect audit log')

    @app.cli.command('set-password')
    @click.argument('username')
    @click.password_option()
    def set_password(username,password):
        if not 12<=len(password)<=1024:
            raise click.ClickException('Use a password between 12 and 1024 characters')
        db=get_db()
        cursor=db.execute('UPDATE users SET password_hash=? WHERE username=?',
                          (generate_password_hash(password),username))
        if not cursor.rowcount:
            raise click.ClickException('User does not exist')
        db.commit();click.echo('Password updated. Rotate SECRET_KEY to invalidate all current sessions when needed.')

    @app.cli.command('probe-sources')
    def probes():
        db=get_db()
        for key in SOURCES:
            status,message=probe(key)
            db.execute('UPDATE sources SET status=?,message=?,checked_at=? WHERE id=?',(status,message,now(),key))
            db.commit(); click.echo(f'{key}: {status} — {message}')

    @app.cli.command('sync')
    @click.argument('source',type=click.Choice(['nse','data_gov']))
    @click.option('--as-of',required=True,help='Source publication date, not an inferred freshness date')
    @click.option('--offset',default=0,type=click.IntRange(min=0))
    @click.option('--max-pages',default=100,type=click.IntRange(min=1,max=10000))
    def sync(source,as_of,offset,max_pages):
        try:
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/f'{source}.csv'
                if source=='nse':
                    download_nse(path)
                    kind='securities'
                else:
                    _,next_offset=download_data_gov(path,offset,max_pages)
                    click.echo(f'Next offset: {next_offset}'); kind='companies'
                result=ingest(get_db(),path,kind,source,as_of)
                click.echo(json.dumps(result,indent=2))
                if result['status'] in ('partial','failed'):
                    raise click.ClickException('Import has rejected records')
        except (SourceError, __import__('requests').RequestException):
            # API exceptions may include credential-bearing query strings; do not print them.
            raise click.ClickException('Official source unavailable or configuration/schema invalid; inspect source requirements. No records imported.') from None

    return app
