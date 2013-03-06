import rbusys


class EMailInterface(rbusys.SinglePlug):
    def send(self, toaddrs, subject, body, attachments={}):
        """send e-mail

        toaddrs - List of receipients
        subject - E-Mail subject
        body - E-Mail text
        attachments - optional, dict with
                            keys = filename (as seen by mail client)
                            value = content as string or file-like object
        """
        pass
