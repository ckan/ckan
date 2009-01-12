import imaplib
import smtplib
import email
from email.mime.text import MIMEText

from pylons import config

def create_msg(text, **kwargs):
    msg = MIMEText(text)
    from_email = 'data-enquire@okfn.org'
    msg['From'] = from_email
    msg['Reply-To'] = from_email
    for k,v in kwargs.items():
        msg[k.capitalize()] = v
    return msg

class Gmail(object):
    '''Inteface to gmail via imap and smtp.'''
    def __init__(self, user, pwd):
        self.user = user
        self.pwd = pwd

    def unread(self):
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(self.user, self.pwd)
        mail.select('Inbox')
        typ, data = mail.search(None, 'UNSEEN')

        results = []
        for num in data[0].split():
            typ, data = mail.fetch(num, '(RFC822)')
            if typ == 'OK':
                msg = email.message_from_string(data[0][1])
                results.append(msg)
            # print 'Message %s\n%s\n' % (num, data[0][1])
        mail.close()
        mail.logout()
        return results

    def send(self, msg):
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(self.user, self.pwd)
        s.sendmail(msg['From'], msg['To'], msg.as_string())
        s.close()
        # Should be s.quit(), but that crashes...
        s.close()

    @classmethod
    def default(self):
        '''Return a default Gmail instance based on config in your ini file.'''
        if config.get('enquiry.email_user', ''):
            USER = config['enquiry.email_user']
            PWD = config['enquiry.email_pwd']
            return Gmail(USER, PWD)
        else:
            return None
