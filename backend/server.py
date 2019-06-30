import falcon
import os
import sys
import urllib
import subprocess
from dateutil import parser
import json

import jinja2
import psycopg2

this_dir = os.path.dirname(os.path.abspath(__file__))
def log(message):
    with open(os.path.join(this_dir, 'logs.txt'), 'a') as fa:
        print(message, file=fa)
sys.path.insert(0, this_dir)

from helpers import load_keys

def get_db_connection():
    return psycopg2.connect('postgres://localhost')

class HTTPSResource(object):
    """docstring for HTTPSResource"""
    reload_templates = True
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(this_dir, 'templates')))

    keydict = load_keys()

    def __init__(self, *args, **kwargs):
        super(HTTPSResource, self).__init__(*args, **kwargs)
        # self.https = os.environ['HTTPS'].lower() == 'true'
        self.https = True

    def on_get(self, req, resp):

        if self.https and req.scheme.lower() == 'http':
            raise falcon.HTTPMovedPermanently(
                req.url.replace('http', 'https', 1)
            )
        if req.params.get('key', None) not in self.keydict:
            raise falcon.HTTPUnauthorized()

    @staticmethod
    def get_key_param_str(req):
        key = req.params.get('key', None)
        key = 'key={}'.format(key) if key else ''
        return key

    @staticmethod
    def parse_post_data(req):
        raw = req.bounded_stream.read().decode()
        raw = raw.replace('+', ' ')
        data = dict()
        for d in raw.split('&'):
            try:
                k, v = d.split('=')
            except:
                msg = "couldn't parse '{}'".format(d)
                log(msg)
                print(msg)
                raise
            k = urllib.parse.unquote(k).replace('\\r\\n', '\n')
            v = urllib.parse.unquote(v).replace('\\r\\n', '\n')
            data[k] = v
        return data

    @staticmethod
    def _parse_time(timestr):
        time = timestr.strip() or None
        if time:
            time = subprocess.check_output('date -d"{}"'.format(time), shell=True).decode().strip()
            time = parser.parse(time)
        return time


class RootResource(HTTPSResource):
    def on_get(self, req, resp):
        super(RootResource, self).on_get(req, resp)
        resp.content_type = falcon.MEDIA_HTML
        resp.body = """
            <html><head>
            <meta http-equiv="Refresh" content="1; url=index.html?{key}">
            </head><body>
            Redirecting in 1 second...
            </body></html>
        """.format(
            key=self.get_key_param_str(req),
        )

class IndexResource(HTTPSResource):
    def __init__(self, *args, **kwargs):
        super(IndexResource, self).__init__(*args, **kwargs)
        self.template = self._load_template()

    def on_get(self, req, resp):
        super(IndexResource, self).on_get(req, resp)
        resp.content_type = falcon.MEDIA_HTML
        key = req.params.get('key', None)
        key = 'key={}'.format(key) if key else ''

        template = self.template
        if self.reload_templates:
            template = self._load_template()

        resp.body = template.render(key=key)
        return

    @classmethod
    def _load_template(cls):
        with open(os.path.join(this_dir, 'templates/index.html'), 'r') as fr:
            template = cls.jinja_env.from_string(fr.read())
        return template


class FoodResource(HTTPSResource):
    conn = get_db_connection()
    human_to_cpu = {
        'date': 'dt',
    }
    cpu_to_human = {
        v: k for k, v in human_to_cpu.items()
    }

    def __init__(self, *args, **kwargs):
        super(FoodResource, self).__init__(*args, **kwargs)

    def rows_to_html_table(self, cursor, req):
        key = self.get_key_param_str(req)
        columns = [c.name for c in cursor.description]
        original_columns = columns.copy()
        # print('original_columns:', original_columns)
        columns.append('actions')
        columns.remove('deleted')
        headers = ['            <th>{}</th>'.format(c) for c in columns]
        rows = list()
        for row in cursor:
            # print(row)
            row_dict = dict(zip(original_columns, row))

            fid = row_dict['fid']

            this_row = list()
            # https://stackoverflow.com/questions/1249688/html-is-it-possible-to-have-a-form-tag-in-each-table-row-in-a-xhtml-valid-way
            this_row.append(f'''
                <td>
                    <form id="form{fid}" action="food?{key}" class="update_food"></form>
                    {row_dict["fid"]}
                    <input form="form{fid}" type="hidden" name="fid" value="{row_dict["fid"]}">
                </td>
            '''.format(fid=fid, key=key))
            this_row.append(f'<td><input form="form{fid}" type="text" name="food" value="{row_dict["food"]}"></td>')
            this_row.append(f'<td>{row_dict["dt"]}</td>')
            this_row.append(f'<td><input form="form{fid}" type="text" name="location" value="{row_dict["location"]}"></td>')
            this_row.append(f'<td><input form="form{fid}" type="text" name="price" value="{row_dict["price"]}"></td>')
            this_row.append(f'<td><input form="form{fid}" type="text" name="count" value="{row_dict["count"]}"></td>')
            this_row.append(f'<td><input form="form{fid}" type="text" name="unit" value="{row_dict["unit"]}"></td>')
            # this_row.append(f'<td>{row_dict["deleted"]}</td>')
            this_row.append(f'<td>{row_dict["price_per_unit"]}</td>')
            this_row.append(f'''<td>
                <input type="button" value="Delete" onclick="delete_food_by_fid({row_dict["fid"]})">
                <input form="form{fid}" type="submit" value="Update" class="update_food_button">
            </td>''')

            # print('row:', row)
            # print('row_dict:', row_dict)
            rows.append('''<tr>\n{row}</tr>'''.format(
                fid=row_dict["fid"],
                row='\n'.join(
                    '            {}'.format(v)
                    for v in this_row
                ),
                key=key,
            ))
        # print('rows:', rows[0])
        return """
        <table id="food_search">
            <tr>\n{headers}
            </tr>
            {rows}
        </table>
        """.format(
            headers='\n'.join(headers),
            rows='\n'.join(rows),
        )

    def on_get(self, req, resp):
        super(FoodResource, self).on_get(req, resp)
        search_terms = req.params['search_terms'].split()
        query = '''SELECT
            *
            , '$'||round(price/count, 3)||'/'||unit AS price_per_unit
        FROM groceries.foods
        WHERE NOT DELETED AND {};'''.format(
            ' AND '.join(
                "food ilike '%{food}%'".format(food=st)
                for st in search_terms
            )
        )
        # query = 'select * from groceries.foods'
        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
        except:
            self.conn.rollback()
            return
        html_table = self.rows_to_html_table(cursor, req)
        cursor.close()

        resp.body = html_table
        resp.content_type = falcon.MEDIA_TEXT
        return

        # data = self.parse_post_data(req)

        # resp.body = str(data)
        return

    def on_post(self, req, resp):
        data = self.parse_post_data(req)
        response = dict()

        fields = 'food location price'.split()
        values = [
            "%({})s".format(f) for f in fields
        ]
        for f in 'date count unit'.split():
            if f in data and data[f]:
                if f in self.human_to_cpu:
                    f2 = self.human_to_cpu[f]
                    data[f2] = data[f]
                    del data[f]
                else:
                    f2 = f

                fields.append(f2)
                values.append("%({})s".format(f2))

        query = """INSERT INTO groceries.foods
            ({fields})
            values
            ({values})
        """.format(
            fields=','.join(fields),
            values=','.join(values),
        )

        cursor = self.conn.cursor()
        try:
            cursor.execute(query, data)
        except psycopg2.DataError as e:
            response['message'] = str(e)
            response['success'] = False
            self.conn.rollback()
            resp.content_type = falcon.MEDIA_JSON
            resp.body = json.dumps(response)
        else:
            response['message'] = str(data)
            response['success'] = True
            self.conn.commit()
        finally:
            cursor.close()
            resp.content_type = falcon.MEDIA_JSON
            resp.body = json.dumps(response)

    def on_put(self, req, resp):
        response = dict()
        data = self.parse_post_data(req)

        columns = data.keys()

        query = """UPDATE groceries.foods
            SET {columns}
            WHERE fid=%(fid)s
        """.format(
            columns=','.join(['{c}=%({c})s'.format(c=c) for c in columns]),
        )

        cursor = self.conn.cursor()
        try:
            cursor.execute(query, data)
        except psycopg2.DataError as e:
            response['message'] = str(e)
            response['success'] = False
            self.conn.rollback()
        else:
            response['message'] = str(data)
            response['success'] = True
            self.conn.commit()
        finally:
            cursor.close()
            resp.content_type = falcon.MEDIA_JSON
            resp.body = json.dumps(response)

    def on_delete(self, req, resp):
        data = self.parse_post_data(req)

        response = dict()

        cursor = self.conn.cursor()
        query = '''UPDATE groceries.foods
            SET deleted=true
            WHERE fid=%(fid)s;
        '''
        try:
            cursor.execute(query, data)
        except psycopg2.DataError as e:
            response['message'] = str(e)
            response['success'] = False
            self.conn.rollback()
            resp.content_type = falcon.MEDIA_JSON
        else:
            response['message'] = str(data)
            response['success'] = True
            self.conn.commit()
        finally:
            cursor.close()
            resp.body = json.dumps(response)


class CreateResource(HTTPSResource):
    conn = get_db_connection()

    def __init__(self, *args, **kwargs):
        super(CreateResource, self).__init__(*args, **kwargs)



api = falcon.API()

api.add_route('/', RootResource())
api.add_route('/index.html', IndexResource())
api.add_route('/food', FoodResource())
