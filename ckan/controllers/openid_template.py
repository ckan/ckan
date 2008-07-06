import pylons
from pylons.templating import Buffet
from pylons import config
import ckan.lib.helpers as h
from ckan.lib.app_globals import Globals

class MyBuffet(Buffet):
    def _update_names(self, ns):
        return ns

def_eng = config['buffet.template_engines'][0]

buffet = MyBuffet(
    def_eng['engine'],
    template_root=def_eng['template_root'],
    **def_eng['template_options']
)

for e in config['buffet.template_engines'][1:]:
    buffet.prepare(
        e['engine'],
        template_root=e['template_root'],
        alias=e['alias'],
        **e['template_options']
    )

class State:
    def __getitem__(self,v):
        return ''
c = State()

g=Globals()

def make_template():
    ''' In the following call, namespace is a dictionary of stuff for the templating
    engine ... which is why c is a (nearly) empty class, and h is the normal helper '''
    return buffet.render(
        template_name="account/openid_form",
        namespace=dict(h=h, g=g, c=State())
    ).replace("%", "%%").replace("FORM_ACTION", "%s").replace("DOLAR", "$")

