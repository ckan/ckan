from typing import Optional

from ckan.plugins import toolkit


def popular(type_: str,
            number: int,
            min: int = 1,
            title: Optional[str] = None) -> str:
    ''' display a popular icon. '''
    if type_ == 'views':
        title = toolkit.ungettext('{number} view', '{number} views', number)
    elif type_ == 'recent views':
        title = toolkit.ungettext(
            '{number} recent view', '{number} recent views', number
            )
    elif not title:
        raise Exception('popular() did not recieve a valid type_ or title')
    data_dict = {'title': title, 'number': number, 'min': min}

    return toolkit.render_snippet('snippets/popular.html', data_dict)
