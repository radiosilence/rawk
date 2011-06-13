from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

from flaskext.markdown import Markdown

import logging
from logging import Formatter, FileHandler

import json
import redis

from local_settings import *


def config(debug=None):
    if debug:
        print "Debug mode."
#        static_types = [
#            'ico'
#        ]
        app = Flask(__name__)

    else:
#        static_types = [
#            'gif', 'jpg', 'jpeg', 'css', 'gif', 'woff', 'ttf', 'ico', 'js'
#        ]
        app = Flask(__name__, static_path='/')

    app.config.from_object(__name__)
    app.config.from_envvar('RAWK_SETTINGS', silent=True)
    Markdown(app)

    return app

app = config(debug=DEBUG)

redis_connection = redis.Redis(
    host=app.config['REDIS_HOST'],
    port=app.config['REDIS_PORT'],
    db=app.config['REDIS_DB']
)


if not app.debug:
    file_handler = FileHandler('error.log', encoding="UTF-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(funcName)s:%(lineno)d]'
    ))
    app.logger.addHandler(file_handler)
    print "Added log handler."


@app.before_request
def before_request():
    g.WIKI_NAME = app.config['WIKI_NAME']
    g.r = redis_connection


@app.route('/')
def home():
    return redirect(url_for('article', article_name='home'))


@app.route('/new')
def new():
    return edit_article(article_name='', new=True)


@app.route('/articles')
def list():
    return render_template('list.html',
        articles=g.r.lrange('articles', 0, -1))


@app.route('/dump')
def dump():
    articles = {}
    for a in g.r.lrange('articles', 0, -1):
        articles[a] = g.r.get('article:%s' % a)
    return json.dumps(articles)


@app.route('/config/<string:article_name>')
def confirm_delete(article_name):
    return render_template('confirm.html',
        title='Confirm Delete',
        article_name=article_name)


@app.route('/delete/<string:article_name>')
def delete(article_name):
    g.r.delete('article:%s' % article_name)
    g.r.lrem('articles', article_name, 0)
    flash('Article "%s" has been deleted.' % article_name)
    return redirect(url_for('home'))


@app.route('/save', methods=['POST'])
def save():
    article_name = request.form['article_name']
    content = request.form['content']
    if request.form['new'] == 'True':
        new = True
    else:
        new = False
    print article_name, new, content
    try:
        if '/' in article_name:
            raise Exception('Please do not use slashes in article name.')
        if len(article_name) < 1:
            raise Exception('Article name must be one character or more.')
        g.r.set('article:%s' % article_name, content)
        if new:
            g.r.lpush('articles', article_name)
        flash('Saved article "%s".' % article_name)
        return redirect(url_for('article', article_name=article_name))
    except Exception as e:
        flash(str(e), 'error')

    return edit_article(
        article_name=article_name,
        new=new,
        content=content
    )


@app.route('/edit/<string:article_name>')
def edit(article_name):
    return edit_article(article_name=article_name)


def edit_article(article_name=None, new=False, content=None):
    if not content:
        if not new:
            content = g.r.get('article:%s' % article_name)
        else:
            content = ""
    return render_template('edit.html',
        title=article_name,
        content=content,
        new=new)


@app.route('/<string:article_name>')
def article(article_name):
    if not g.r.exists('article:%s' % article_name):
        return edit_article(article_name=article_name, new=True)
    else:
        content = g.r.get('article:%s' % article_name)
    return render_template('article.html',
      title=article_name,
      content=content.decode('utf-8'))
