import os
from json import dumps
import logging
from logging import FileHandler

from flask import Flask, g, Response, request
from py2neo import Graph

app = Flask(__name__, static_url_path='/static/')

#url = 'bolt://127.0.0.1:7687'
url = 'bolt://10.220.26.89:7687'
password = 'yuanta'
graph = Graph(url, password=password)

def serialize_stream(sub,child):
    return {
        'name': sub['name'],
        'id':sub['subindustry_id'],
        'stream': child['stream']
    }
def serialize_exec(stock):
    return {
        'name': stock['name'],
        'code': stock['code']
    }
def serialize_ind(ind,sub,stream,flag):
    if flag==1:
        return {
            'name': ind['name'],#最大
            'subname': sub['name'],#最小
            'stream_name': stream['stream_name'],#次大
            'stream': stream['stream'],#游
            'submd5': sub['subindustry_id'],#序號
        }
    else:
        return{
            'name': 'nan',#最大
            'subname': 'nan',#最小
            'stream_name': 'nan',#次大
            'stream': 'nan',#游
            'submd5': 'nan',#序號
            }

@app.route('/')
def index():
    return app.send_static_file('index_industry_old.html')


@app.route("/search")
def get_search():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        query = f'''
            MATCH (i:Industry)<-[stream:child_of]-(c:Subindustry)<-[:subindustry_of]-(s:Stock{{code:'{q}'}})
            RETURN s, c, i, stream
            '''
        query2 = f'''
            MATCH (s:Stock{{code:'{q}'}})-[:indexclass_of]->(indexclass:IndexClass)
            RETURN s,indexclass
            '''
        results = graph.run(query).data()
        results2 = graph.run(query2).data()
        flag=1
        try:####原本的資料沒有的；cmoney有的走這邊
            code=results[0]['s']['code']
            name=results[0]['s']['name']
        except:
            code=results2[0]['s']['code']
            name=results2[0]['s']['name']
            flag=0
            results.append({'i':'what','c':'the','stream':'s'})
            #app.logger.info(code,name)
        try:####原本的資料有的；cmoney沒有的走這邊
            indexclass=results2[0]['indexclass']['name']
            index_code=results2[0]['indexclass']['indexclass_id']
        except:
            indexclass='nan'
            index_code=0
        return Response(dumps({"stock_code": code,
                               "stock_name": name,
                               "indexclassname": indexclass,
                               "index_code": index_code,
                               "Industry_stream": [serialize_ind(result['i'],result['c'],result['stream'],flag) for result in results]}),
                        mimetype="application/json")


@app.route("/sub/<sub>")
def get_sub(sub):
    query = f'''
            MATCH (c:Subindustry{{subindustry_id:'{sub}'}})<-[:subindustry_of]-(s:Stock)
            RETURN s, c
            '''

    results = graph.run(query).data()

    return Response(dumps({"stock_code": results[0]['s']['code'],
                           "sub_name": results[0]['c']['name'],
                           "stock_name": results[0]['s']['name'],
                           "stock": [serialize_exec(result['s']) for result in results]
                           }),
                    mimetype="application/json")

@app.route("/index/<indexclass>")
def get_index(indexclass):
    query = f'''
            MATCH (i:IndexClass{{indexclass_id:'{indexclass}'}})<-[:indexclass_of]-(s:Stock)
            RETURN s,i
            '''

    results = graph.run(query).data()

    return Response(dumps({"index_name": results[0]['i']['name'],
                           "stock": [serialize_exec(result['s']) for result in results]
                           }),
                    mimetype="application/json")

@app.route("/industry/<ind>")
def get_child(ind):
    query = f'''
            MATCH (i:Industry{{name:'{ind}'}})<-[c:child_of]-(s:Subindustry)
            RETURN s,c,i
            ORDER BY c.stream
            '''

    results = graph.run(query).data()

    return Response(dumps({"industryname": results[0]['i']['name'],
                           "subchild": [serialize_stream(result['s'],result['c']) for result in results]
                           }),
                    mimetype="application/json")



## 希望跟查詢連動，跳出來的是，查詢股票的所有董事、概念股、產業別、以及買賣分點
## 改回傳格式
## node: id, name, lable(entity type), pageranke(todo)
## link: source, target, type
@app.route("/graph")
def get_graph():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        query = f'''
                MATCH (s:Stock{{code:'{q}'}}) 
                MATCH p=(s)-[rels:subindustry_of]-(others)
                RETURN s, rels, others
                '''

        results = graph.run(query).data()


        nodes = []
        rels = []
        _id = 1
        nodes.append({"id": 0,
                      "name": results[0]['s']['name'], 
                      "label": set(results[0]['s'].labels).pop()})

        for result in results:
            nodes.append({"id": _id,
                          "name": result['others']['name'], 
                          "label": set(result['others'].labels).pop()})
            rels.append({"source": 0, 
                         "target": _id,
                         "type":type(result['rels']).__name__})
            _id += 1

    return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")



if __name__ == '__main__':
    app.debug = True
    handler = logging.FileHandler('flask.log')
    app.logger.addHandler(handler)
    app.logger.info('Running the graph database at %s', url)
    app.run(host='10.220.26.89',port=4000)
