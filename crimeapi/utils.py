import urllib
import urlparse
import hmac
import base64
import hashlib
import os

def encoded_dict(in_dict):
    out_dict = {}
    for k, v in in_dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
        # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    return out_dict

def make_meta(crimes):
    out =  {
        'total': {'key': 'total', 'name': 'Total', 'value': len(crimes)},
        'detail': [
            {'key': 'arson', 'name': 'Arson', 'value': len([c for c in crimes if c.get('primary_type') == 'ARSON'])},
            {'key': 'assault', 'name': 'Assault', 'value': len([c for c in crimes if c.get('primary_type') == 'ASSAULT'])},
            {'key': 'battery', 'name': 'Battery', 'value': len([c for c in crimes if c.get('primary_type') == 'BATTERY'])},
            {'key': 'burglary', 'name': 'Burglary', 'value': len([c for c in crimes if c.get('primary_type') == 'BURGLARY'])},
            {'key': 'crim_sexual_assault', 'name': 'Criminal Sexual Assault', 'value': len([c for c in crimes if c.get('primary_type') == 'CRIM SEXUAL ASSAULT'])},
            {'key': 'criminal_damage', 'name': 'Criminal Damage', 'value': len([c for c in crimes if c.get('primary_type') == 'CRIMINAL DAMAGE'])},
            {'key': 'criminal_trespass', 'name': 'Criminal Trespass', 'value': len([c for c in crimes if c.get('primary_type') == 'CRIMINAL TRESPASS'])},
            {'key': 'deceptive_practice', 'name': 'Deceptive Practice', 'value': len([c for c in crimes if c.get('primary_type') == 'DECEPTIVE PRACTICE'])},
            {'key': 'domestic_violence', 'name': 'Domestic Violence', 'value': len([c for c in crimes if c.get('primary_type') == 'DOMESTIC VIOLENCE'])},
            {'key': 'gambling', 'name': 'Gambling', 'value': len([c for c in crimes if c.get('primary_type') == 'GAMBLING'])},
            {'key': 'homicide', 'name': 'Homicide', 'value': len([c for c in crimes if c.get('primary_type') == 'HOMICIDE'])},
            {'key': 'interfere_with_public_officer', 'name': 'Interfere with Public Officer', 'value': len([c for c in crimes if c.get('primary_type') == 'INTERFERE WITH PUBLIC OFFICER'])},
            {'key': 'interference_with_public_officer', 'name': 'Interference with Public Officer', 'value': len([c for c in crimes if c.get('primary_type') == 'INTERFERENCE WITH PUBLIC OFFICER'])},
            {'key': 'intimidation', 'name': 'Intimidation', 'value': len([c for c in crimes if c.get('primary_type') == 'INTIMIDATION'])},
            {'key': 'kidnapping', 'name': 'Kidnapping', 'value': len([c for c in crimes if c.get('primary_type') == 'KIDNAPPING'])},
            {'key': 'liquor_law_violation', 'name': 'Liquor Law Violation', 'value': len([c for c in crimes if c.get('primary_type') == 'LIQUOR LAW VIOLATION'])},
            {'key': 'motor_vehicle_theft', 'name': 'Motor Vehicle Theft', 'value': len([c for c in crimes if c.get('primary_type') == 'MOTOR VEHICLE THEFT'])},
            {'key': 'narcotics', 'name': 'Narcotics', 'value': len([c for c in crimes if c.get('primary_type') == 'NARCOTICS'])},
            {'key': 'non_criminal', 'name': 'Non-Criminal', 'value': len([c for c in crimes if c.get('primary_type') == 'NON-CRIMINAL'])},
            {'key': 'non_criminal_subject_specified', 'name': 'Non-Criminal (Subject Specified)', 'value': len([c for c in crimes if c.get('primary_type') == 'NON-CRIMINAL (SUBJECT SPECIFIED)'])},
            {'key': 'obscenity', 'name': 'Obscenity', 'value': len([c for c in crimes if c.get('primary_type') == 'OBSCENITY'])},
            {'key': 'offense_involving_children', 'name': 'Offense Involving Children', 'value': len([c for c in crimes if c.get('primary_type') == 'OFFENSE INVOLVING CHILDREN'])},
            {'key': 'offenses_involving_children', 'name': 'Offenses Involving Children', 'value': len([c for c in crimes if c.get('primary_type') == 'OFFENSES INVOLVING CHILDREN'])},
            {'key': 'other_narcotic_violation', 'name': 'Other Narcotic Violation', 'value': len([c for c in crimes if c.get('primary_type') == 'OTHER NARCOTIC VIOLATION'])},
            {'key': 'other_offense', 'name': 'Other Offense', 'value': len([c for c in crimes if c.get('primary_type') == 'OTHER OFFENSE'])},
            {'key': 'prostitution', 'name': 'Prostitution', 'value': len([c for c in crimes if c.get('primary_type') == 'PROSTITUTION'])},
            {'key': 'public_indecency', 'name': 'Public Indecency',  'value': len([c for c in crimes if c.get('primary_type') == 'PUBLIC INDECENCY'])},
            {'key': 'public_peace_violation', 'name': 'Public Peace Violation', 'value': len([c for c in crimes if c.get('primary_type') == 'PUBLIC PEACE VIOLATION'])},
            {'key': 'ritualism', 'name': 'Ritualism', 'value': len([c for c in crimes if c.get('primary_type') == 'RITUALISM'])},
            {'key': 'robbery', 'name': 'Robbery', 'value': len([c for c in crimes if c.get('primary_type') == 'ROBBERY'])},
            {'key': 'sex_offense', 'name': 'Sex Offense', 'value': len([c for c in crimes if c.get('primary_type') == 'SEX OFFENSE'])},
            {'key': 'stalking', 'name': 'Stalking', 'value': len([c for c in crimes if c.get('primary_type') == 'STALKING'])},
            {'key': 'theft', 'name': 'Theft', 'value': len([c for c in crimes if c.get('primary_type') == 'THEFT'])},
            {'key': 'weapons_violation', 'name': 'Weapons Violation', 'value': len([c for c in crimes if c.get('primary_type') == 'WEAPONS VIOLATION'])},
        ]
    }
    return out
