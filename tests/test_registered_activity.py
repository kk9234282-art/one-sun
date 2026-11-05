import pytest
from intelligence.registered_activity import details,matches,reference
from scripts.prepare_cin_reference import parse_2004


def test_exact_liquor_code_has_version_label_and_no_current_business_claim():
    row=details('U15511MH2010PTC000001')
    assert row['registered_activity_code']=='15511'
    assert row['registered_activity_status']=='reference_candidate'
    assert row['registered_activity_candidates']==[{'edition':'2004','reference_code':'15511','level':5,'description':'Manufacture of country liquor'}]


def test_conflicting_editions_and_broad_legacy_matches_are_retained():
    row=details('U72200MH2010PTC000001')
    assert row['registered_activity_status']=='multiple_candidates'
    old,new=row['registered_activity_candidates']
    assert old['edition']=='2004' and old['reference_code']=='722' and old['level']==3
    assert 'Software' in old['description']
    assert new['edition']=='2008' and new['reference_code']=='72200' and new['level']==5
    assert 'social sciences' in new['description']
    assert 'broad 3-digit match' in row['registered_activity']


def test_no_prefix_guess_for_nonzero_unknown_subclass_or_invalid_cin():
    assert details('U99999MH2010PTC000001')['registered_activity_status']=='unmapped'
    assert details('U01198MH2010PTC000001')['registered_activity_status']=='unmapped'
    assert details('invalid')['registered_activity_code'] is None
    assert matches('U15511MH2010PTC000001','liquor','reference_candidate')
    assert not matches('U15511MH2010PTC000001','software','')


def test_reference_parser_excludes_alphabetic_repair_subclasses_and_numeric_notes():
    text='''        2899            Other metal products
                28998   Manufacture of metal goods for office use
                28998   Repair and maintenance of other fabricated metal products
                (A)
                         6022 and 6023 are cross references in explanatory notes.
                    90001   Garbage collection, transportation and disposal'''
    rows=parse_2004(text)
    assert rows['28998']=='Manufacture of metal goods for office use'
    assert '6022' not in rows
    assert rows['90001']=='Garbage collection, transportation and disposal'


def test_reference_sizes_and_edition_collisions():
    refs=reference()['references']
    assert sum(len(k)==5 for k in refs['2004'])==1184
    assert sum(len(k)==5 for k in refs['2008'])==1304
    assert refs['2004']['01111']!=refs['2008']['01111']
