from wtforms import TextField


def DBField(db_field):
    """create WTForm Field from rw.db attribute"""
    # title = db_field.title
    return TextField('1' ) # db_field.title)
