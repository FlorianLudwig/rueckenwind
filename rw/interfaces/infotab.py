import rbusys


class InfoTab(rbusys.MultiPlug):
    rbus_path = 'rw.infotab'

    def get_name(self):
        return "Unnamed Tab"

    def get_content(self):
        return "Please implement get_content()"
