"""
Flask integration for i18n.

Usage:
    from i18n.flask_integration import I18n

    i18n = I18n(default='ru')
    i18n.load_dir('i18n/translations')
    i18n.init_app(app)

    In templates: {{ t('key') }}
    In routes:    t('key')
    Switch lang:  POST /set-lang  (form field: lang)
"""
from functools import wraps
from flask import Flask, session, request, g


def I18nExtension(i18n_instance):
    """Create a Flask extension from an i18n instance."""

    def init_app(app: Flask):
        app.config['I18N'] = i18n_instance

        @app.before_request
        def _set_lang():
            if request.method == 'POST' and 'lang' in request.form:
                lang = request.form['lang']
                if lang in i18n_instance.langs():
                    session['lang'] = lang
                    i18n_instance.set_lang(lang)
            elif 'lang' in session:
                i18n_instance.set_lang(session['lang'])
            elif request.args.get('lang') in i18n_instance.langs():
                lang = request.args['lang']
                session['lang'] = lang
                i18n_instance.set_lang(lang)

        @app.context_processor
        def _inject():
            return {
                't': i18n_instance.t,
                'current_lang': i18n_instance.current,
                'langs': i18n_instance.langs(),
            }

    return init_app
