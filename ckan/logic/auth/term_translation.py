from __future__ import annotations



from ckan.common import _

from ckan.types import AuthResult, Context, DataDict





def term_translation_show(context: Context, data_dict: DataDict) -> AuthResult:
    '''Check if the translations for the given term(s) and language(s) are visible.
    Visible to all by default.'''
    return {'success': True}

def term_translation_update(context: Context,
                            data_dict: DataDict) -> AuthResult:
    # sysadmins only
    user = context['user']
    return {
        'success': False,
        'msg': _('User %s not authorized to update term_translation table') % user
    }
