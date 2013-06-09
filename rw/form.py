from . import db
from wtforms import TextField, validators


def DBField(db_field):
    """create WTForm Field from rw.db attribute"""
    # title = db_field.title
    validator_list = []
    if db_field.default is db.NoDefaultValue:
        validator_list.append(validators.Required())
    return TextField(db_field.name, validator_list) # db_field.title)
