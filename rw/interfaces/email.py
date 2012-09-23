import rbusys


class EMailInterface(rbusys.SinglePlug):
    def send(self, toaddrs, subject, body):
        """send e-mail

        toaddrs - List of receipients
        subject - E-Mail subject
        body - E-Mail text
        """
        pass
