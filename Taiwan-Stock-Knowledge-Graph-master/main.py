import os
from json import dumps
import logging
from logging import FileHandler

from flask import Flask, g, Response, request
from py2neo import Graph

app = Flask(__name__, static_url_path='/static/')

url = 'bolt://127.0.0.1:7687'
#url = 'bolt://10.220.26.89:7687'
password = 'yuanta'
graph = Graph(url, password=password)
def serialize_concept_stock(stock):
        return {
            'name': stock['name'],#最大
            'code': stock['code']#最小
            }
def serialize_stream(sub,child):
    return {
        'name': sub['name'],
        'id':sub['subindustry_id'],
        'stream': child['stream']
    }
def serialize_stock(stock):
    return {
        'name': stock['name'],
        'code': stock['code']
    }

def serialize_execution(r,n):
    return {
        'name': n['name'],
        'jobs': r['ENGname'],
        'stock_num': r['stock_weight']
    }
def serialize_exec(r,n):
    return {
        'name': n['name'],
        'manager': r['manager'],
        'spokesman': r['spokesman'],
        'occupation': r['occupation'],
        'address': r['address'],
        'company': r['company']
    }
def serialize_qchange(r,n):
    return {
        'company': r['company'],
        'name': n['name'],
        'region': r['region'],
        'weight': r['weight']
    }
def serialize_region(stock):
    return {
        'name':stock['name'],
        'code':stock['code']
    }
def serialize_ind(result1,result2,result4,result5):

    return {
        'name': result1['i']['name'],#最大
        'subname': result1['c']['name'],#最小
        'submd5': result1['c']['subindustry_id'],#序號
        'stream': result1['stream']['stream'],
        'subnamenew':result2['c']['name'],
        'subnewmd5':result2['c']['subindustry_new_id'],
        'conceptname':result4['c']['name'],#最大
        'concept_id':result4['c']['concept_id'],#最小
        'conceptname2':result5['c']['name'],#最大
        'concept_id2':result5['c']['concept_id']#最小
    }


@app.route('/')
def index():
    return app.send_static_file('index_whole.html')


@app.route("/search")
def get_search():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        if q.isdigit():
            query = f'''
                MATCH (i:Industry)<-[stream:child_of]-(c:Subindustry)<-[:subindustry_of]-(s:Stock{{code:'{q}'}})
                RETURN s, c, i, stream
                '''
            query2 = f'''
                MATCH (i:Industry_new)<-[:child_new_of]-(c:Subindustry_new)<-[:subindustry_new_of]-(s:Stock{{code:'{q}'}})
                RETURN s, c, i
                '''
            query3 = f'''
                MATCH (s:Stock{{code:'{q}'}})-[:indexclass_of]->(indexclass:IndexClass)
                RETURN s,indexclass
                '''
            query4 = f'''
                MATCH (c:Concept)<-[:concept_of]-(s:Stock{{code:'{q}'}})
                RETURN s, c
                '''
            query_stock=f'''
                MATCH (s:Stock{{code:'{q}'}})
                RETURN s
                '''
        else:
            query = f'''
                MATCH (i:Industry)<-[stream:child_of]-(c:Subindustry)<-[:subindustry_of]-(s:Stock{{name:'{q}'}})
                RETURN s, c, i, stream
                '''
            query2 = f'''
                MATCH (i:Industry_new)<-[:child_new_of]-(c:Subindustry_new)<-[:subindustry_new_of]-(s:Stock{{name:'{q}'}})
                RETURN s, c, i
                '''
            query3 = f'''
                MATCH (s:Stock{{name:'{q}'}})-[:indexclass_of]->(indexclass:IndexClass)
                RETURN s,indexclass
                '''
            query4 = f'''
                MATCH (c:Concept)<-[:concept_of]-(s:Stock{{name:'{q}'}})
                RETURN s, c
                '''
            query_stock=f'''
                MATCH (s:Stock{{name:'{q}'}})
                RETURN s
                '''
            print('問號')
        results = graph.run(query).data()
        results2 = graph.run(query2).data()
        results3 = graph.run(query3).data()
        results4 = graph.run(query4).data()
        results_stock = graph.run(query_stock).data()
        #mid=len(results4)//2+len(results4)%2
        results5=[results4[i] for i in range(len(results4)) if i%2==1]
        results4=[results4[i] for i in range(len(results4)) if i%2==0]
        a=[len(results),len(results2),len(results3),len(results4)]
        maxi=max(a)
        print(a)
        wholeresult=[]
        nan1,nan2,nan3,nan4=dict(),dict(),dict(),dict()
        subd,cond,indd,streamd=dict(),dict(),dict(),dict()
        subd['name'],subd['subindustry_new_id'],subd['subindustry_id']='','',''
        cond['name'],cond['concept_id']='',''
        indd['name'],indd['industry_new_id'],indd['industry_id']='','',''
        streamd['stream'],streamd['stream_name']='',''
        nan1['c'],nan1['i'],nan1['stream']=subd,indd,streamd
        nan2['c'],nan2['i']=subd,indd
        nan4['c']=cond
        
        for i in range(maxi):
            try:
                wholeresult.append(results[i])
            except:
                wholeresult.append(nan1)
            try:
                wholeresult.append(results2[i])
            except:
                wholeresult.append(nan2)            
            try:
                wholeresult.append(results4[i])
            except:
                wholeresult.append(nan4)
            try:
                wholeresult.append(results5[i])
            except:
                wholeresult.append(nan4)
        code=results_stock[0]['s']['code']
        name=results_stock[0]['s']['name']
        try:
            indexclass=results3[0]['indexclass']['name']
            index_code=results3[0]['indexclass']['indexclass_id']
        except:
            indexclass='沒連到！'
            index_code='沒連到！'

        return Response(dumps({"stock_code": code,
                               "stock_name": name,
                               "indexclassname": indexclass,
                               "index_code": index_code,
                               "Industry_stream": [serialize_ind(wholeresult[i*4],wholeresult[i*4+1],wholeresult[i*4+2],wholeresult[i*4+3]) for i in range(maxi)]}),
                        mimetype="application/json")
@app.route("/executive/<text>")
def get_executive(text):
    stock,region=text.split(' ')
    query = f'''
            MATCH (m:Stock{{code:'{stock}'}})-[r:holder_of]->(n)
            RETURN m,n, r
            ORDER BY toFloat(r.stock_weight) DESC
            '''
    query2 = f'''
            MATCH (m:Stock{{code:'{stock}'}})-[r:exec_of]->(n)
            RETURN m,n, r
            '''
    if(region=='default'):
        query3 = f'''
                MATCH (m:Stock{{code:'{stock}'}})-[r:Qchange_of]->(n)
                WHERE r.weight =~ '[0-9].*'
                RETURN m,n, r
                ORDER BY toFloat(r.weight) DESC,r.region
                UNION
                MATCH (m:Stock{{code:'{stock}'}})-[r:Qchange_of]->(n)
                WHERE NOT r.weight =~ '[0-9].*'
                RETURN m,n, r
                ORDER BY toFloat(r.weight) DESC,r.region
                '''
    else:
        query3 = f'''
                MATCH (m:Stock{{code:'{stock}'}})-[r:Qchange_of{{type:'{region}'}}]->(n)
                WHERE r.weight =~ '[0-9].*'
                RETURN m,n, r
                ORDER BY toFloat(r.weight) DESC,r.region
                UNION
                MATCH (m:Stock{{code:'{stock}'}})-[r:Qchange_of{{type:'{region}'}}]->(n)
                WHERE NOT r.weight =~ '[0-9].*'
                RETURN m,n, r
                ORDER BY toFloat(r.weight) DESC,r.region
                '''
                #前兩個是一般、大陸or海外，後兩個是放金融資產
    print(stock,region)
    results = graph.run(query).data()
    results2 = graph.run(query2).data()
    results3 = graph.run(query3).data()
    name='查無資料'
    try:
        name=results[0]['m'].end_node['name']
    except:
        print(stock,'沒有主要股東資料')
    try:
        name=results2[0]['m'].end_node['name']
    except:
        print(stock,'沒有董事資料')   
    try:
        name=results3[0]['m'].end_node['name']
    except:
        print(stock,'沒有季轉投資資料')
    
    return Response(dumps({"stock_code": stock,
                           "stock_name": name,
                           "exec": [serialize_exec(result['r'],result['n']) for result in results2],
                           "qchange": [serialize_qchange(result['r'],result['n']) for result in results3],
                           "executive": [serialize_execution(result['r'],result['n']) for result in results]}),
                    mimetype="application/json")
@app.route("/region/<text>")
def get_region(text):
    region=text
    query3 = f'''
            MATCH (m:Stock)-[r:Qchange_of]->(n)
            WHERE r.region CONTAINS '{region}' OR (r.region = '大陸' AND n.name CONTAINS '{region}')
            RETURN DISTINCT m
            ORDER BY toFloat(m.code)
            '''
    print(region)
    results3 = graph.run(query3).data()
    name='查無資料' 
    return Response(dumps({
                            "region":region,
                           "stock": [serialize_region(result['m']) for result in results3],
                           }),
                    mimetype="application/json")
@app.route("/sub/<sub>")
def get_sub(sub):
    query = f'''
            MATCH (c:Subindustry{{subindustry_id:'{sub}'}})<-[:subindustry_of]-(s:Stock)
            RETURN s, c
            ORDER BY toFloat(s.code)
            '''

    results = graph.run(query).data()

    return Response(dumps({"stock_code": results[0]['s']['code'],
                           "sub_name": results[0]['c']['name'],
                           "stock_name": results[0]['s']['name'],
                           "stock": [serialize_stock(result['s']) for result in results]
                           }),
                    mimetype="application/json")
@app.route("/subnew/<sub>")
def get_subnew(sub):
    query = f'''
            MATCH (c:Subindustry_new{{subindustry_new_id:'{sub}'}})<-[:subindustry_new_of]-(s:Stock)
            RETURN s, c
            ORDER BY toFloat(s.code)
            '''
    query2=f'''
            MATCH (cc:Subindustry_new{{subindustry_new_id:'{sub}'}})
            RETURN  cc
            '''
    results = graph.run(query).data()
    results2 = graph.run(query2).data()
    if(len(results)==0):
            return Response(dumps({"stock_code": '無',
                           "sub_name": results2[0]['cc']['name'],
                           "stock_name": '無',
                           "stock": [serialize_stock(result['s']) for result in results]
                           }),
                    mimetype="application/json")
    return Response(dumps({"stock_code": results[0]['s']['code'],
                           "sub_name": results[0]['c']['name'],
                           "stock_name": results[0]['s']['name'],
                           "stock": [serialize_stock(result['s']) for result in results]
                           }),
                    mimetype="application/json")

@app.route("/index/<indexclass>")
def get_index(indexclass):
    query = f'''
            MATCH (i:IndexClass{{indexclass_id:'{indexclass}'}})<-[:indexclass_of]-(s:Stock)
            RETURN s,i
            ORDER BY toFloat(s.code)
            '''

    results = graph.run(query).data()

    return Response(dumps({"index_name": results[0]['i']['name'],
                           "stock": [serialize_stock(result['s']) for result in results]
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

"""
@app.route("/industry/<ind>")
def get_child(ind):
    query = f'''
            MATCH (i:Industry_new{{name:'{ind}'}})<-[c:child_new_of]-(s:Subindustry_new)
            RETURN s,c,i
            '''

    results = graph.run(query).data()

    return Response(dumps({"industryname": results[0]['i']['name'],
                           "subchild": [serialize_stream(result['s'],result['c']) for result in results]
                           }),
                    mimetype="application/json")
"""

@app.route("/concept/<conc>")
def get_concept(conc):
    query = f'''
            MATCH (c:Concept{{concept_id:'{conc}'}})<-[:concept_of]-(s:Stock)
            RETURN s, c
            ORDER BY toFloat(s.code)
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
                MATCH p=(s)-[rels]-(others)
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
    app.run(host='127.0.0.1',port=7777)
