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

def serialize_concept(concept,flag):
    if flag==1:
        return {
            'name': concept['name'],#最大
            'concept_id': concept['concept_id']#最小
        }
    else:
        return{
            'name': 'nan',#最大
            'concept_id': 'nan'#最小
            }
def serialize_concept_stock(stock):
        return {
            'name': stock['name'],#最大
            'code': stock['code']#最小
            }

def serialize_exec(executive):
    return {
        'name': executive.start_node['name'],
        'jobs': executive['jobs'],
        'stock_num': executive['stock_num']
    }
def serialize_index(executive):
    return {
        'name': executive.start_node['name'],
        'code': executive['code'],
    }


@app.route('/')
def index():
    return app.send_static_file('index_concept.html')


@app.route("/search")
def get_search():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        query = f'''
            MATCH (c:Concept)<-[:concept_of]-(s:Stock{{code:'{q}'}})
            RETURN s, c
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
        try:####原本的資料有的；cmoney沒有的走這邊
            indexclass=results2[0]['indexclass']['name']
            index_code=results2[0]['indexclass']['indexclass_id']
        except:
            indexclass='nan'
            index_code=0
        if(len(results)==0):
            return Response(dumps({"stock_code": code,
                       "stock_name": name,
                       "indexclassname":indexclass,
                       "index_code":index_code,
                       "concept": [serialize_concept(result['c'],flag) for result in results]}),
                mimetype="application/json")
        return Response(dumps({"stock_code": code,
                               "stock_name": name,
                               "indexclassname":indexclass,
                               "index_code":index_code,
                               "concept": [serialize_concept(result['c'],flag) for result in results]}),
                        mimetype="application/json")


@app.route("/executive/<stock>")
def get_executive(stock):
    query = f'''
            MATCH (m:Stock{{code:'{stock}'}})<-[r:employ_of]-(n:Person)
            RETURN n, r
            '''

    results = graph.run(query).data()
    if(len(results)==0):
        return Response(dumps({"stock_code": 'nan',
                           "stock_name":'{} - 查無資料'.format(stock),
                           "executive": 'nan'}),
                    mimetype="application/json")
    return Response(dumps({"stock_code": stock,
                           "stock_name": results[0]['r'].end_node['name'],
                           "executive": [serialize_exec(result['r']) for result in results]}),
                    mimetype="application/json")

@app.route("/index/<indexclass>")
def get_index(indexclass):
    query = f'''
            MATCH (i:IndexClass{{indexclass_id:'{indexclass}'}})<-[:indexclass_of]-(s:Stock)
            RETURN s,i
            '''

    results = graph.run(query).data()

    return Response(dumps({"index_name": results[0]['i']['name'],
                           "stock": [serialize_index(result['s']) for result in results]
                           }),
                    mimetype="application/json")

@app.route("/concept/<conc>")
def get_concept(conc):
    query = f'''
            MATCH (c:Concept{{concept_id:'{conc}'}})<-[:concept_of]-(s:Stock)
            RETURN s, c
            '''

    results = graph.run(query).data()

    return Response(dumps({"concept_name": results[0]['c']['name'],
                           "concept_stock": [serialize_concept_stock(result['s']) for result in results]
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
                MATCH p=(s)-[rels:concept_of]-(others)
                RETURN s, rels, others
                '''

        results = graph.run(query).data()

            

        nodes = []
        rels = []
        _id = 1
        if(len(results)==0):
            nodes.append({"id": 0,
                          "name": 'None', 
                          "label": 'None'})
        else:

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
    app.run(host='10.220.26.89',port=3000)
