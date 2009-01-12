import ckan.lib.gmail as G


class TestGmail:
    gmail = G.Gmail.default()
    __test__  = gmail is not None

    out = gmail.unread()

    def _test_send():
        msg = create_msg('testing python api',
            to='data-enquiry@okfn.org',
            )
        self.gmail.send(msg)

    def test_unread(self):
        m1 = self.out[0]
        assert len(self.out) == 2
        assert m1.is_multipart()
        ctype = m1.get_content_type()
        assert ctype == 'multipart/alternative'
        # first part is text/plain, 2nd part is text/html
        submsg = m1.get_payload(0)
        body = submsg.get_payload()
        assert body.startswith('Messages that are easy to find'), body
        msgid = m1['message-id']
        assert msgid == '<b9df8f3e0901090812k69ed71b0x@mail.gmail.com>', msgid

    def test_unread_2(self):
        m2 = self.out[1]
        assert not m2.is_multipart()
        ctype = m2.get_content_type()
        assert ctype == 'text/plain'
        body = m2.get_payload()
        assert body == 'testing python api\r\n', '"%s"' % body


