import grpc
import psycopg2

import similarity_pb2
import similarity_pb2_grpc
import sqlite3
import threading
from concurrent import futures
from sqlalchemy import create_engine

## POSTREG
#db_name = 'database'
#db_user = 'username'
#db_pass = 'secret'
#db_host = 'db'
#db_port = '5432'


class SimilaritySearchService(similarity_pb2_grpc.SimilaritySearchServiceServicer):
    def __init__(self):
        self.connection_pool = threading.local()

        ## POSTREG
        ## Create the database connection
        #self.conn = psycopg2.connect(
        #    dbname=db_name,
        #    user=db_user,
        #    password=db_pass,
        #    host=db_host,
        #    port=db_port
        #)

        # SQLite
    def get_connection(self):
        if not hasattr(self.connection_pool, 'connection'):
            self.connection_pool.connection = sqlite3.connect('similarity.sqlite3')
        return self.connection_pool.connection




    def AddItem(self, request, context):
        description = request.description
        print(f'AddItem:{description}')

        try:
            # SQLite
            connection = self.get_connection()
            cursor = connection.cursor()
            # Create the "items" table if it doesn't exist
            create_db_query = '''CREATE TABLE IF NOT EXISTS items (
                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   description VARCHAR(300))'''
            cursor.execute(create_db_query)
            connection.commit()

            insert_query = "INSERT INTO items (description) VALUES (?)"
            cursor.execute(insert_query, (request.description,))
            connection.commit()
            item = request.description
            len_item = len(item)
            print(f'Len searching item: {len_item}')

            all_items_query = "SELECT id, description FROM items"
            cursor.execute(all_items_query)
            all_result = cursor.fetchall()
            len_all_result = len(all_result)
            print(f"All resultats: {len_all_result}")

            k = []
            for i in range(len_item):
                if i == 0:
                    part_result = item
                else:
                    part_result = item[:-i]

                search_item_in_all_result = sum(1 for it in all_result if part_result in it)
                koefficient = search_item_in_all_result / len_all_result
                k.append(koefficient)

            sum_k = sum(k)
            similarity = (sum_k / len_item)
            print(similarity)
            connection.close()



            ## POSTREG
            #cursor = self.conn.cursor()
            #create_table_query = '''
            #CREATE TABLE IF NOT EXISTS items (
            #    id SERIAL PRIMARY KEY,
            #    description VARCHAR(300)
            #);
            #'''
            #cursor.execute(create_table_query)
            #self.conn.commit()
            #cursor.execute("INSERT INTO items (description) VALUES (%s);", (request.description,))
            #self.conn.commit()
            #item = request.description
            #len_item = len(item)

            #all_items_query = "SELECT id, description FROM items"
            #cursor.execute(all_items_query)
            #all_result = cursor.fetchall()
            #len_all_result = len(all_result)
            #print(f"All resultats: {len_all_result}")
            #k = []
            #for i in range(len_item):
            #    if i == 0:
            #        part_result = item
            #    else:
            #        part_result = item[:-i]

            #    search_item_in_all_result = sum(1 for it in all_result if part_result in it)
            #    koefficient = search_item_in_all_result / len_all_result
            #    k.append(koefficient)

            #sum_k = sum(k)
            #similarity = (sum_k / len_item)
            #print(similarity)
            #cursor.close()


            add_item_response = similarity_pb2.AddItemResponse()
            add_item_response.status = 200
            add_item_response.message = f'Item added successfully: {request.description}' \
                                        f'\nSimilarity: {similarity}'


            return add_item_response
        except sqlite3.Error as e:
            error_response = similarity_pb2.AddItemResponse()
            error_response.status = 500
            error_response.message = 'Error adding item to the database: {}'.format(str(e))

            return error_response

    def SearchItems(self, request, context):
        query = request.query
        print('SearchItems:')
        # SQLite
        connection = self.get_connection()
        cursor = connection.cursor()
        # Execute the search query
        search_query = "SELECT id, description FROM items WHERE description LIKE ?"
        cursor.execute(search_query, ('%' + query + '%',))
        search_results = cursor.fetchall()

        all_items_query = "SELECT id, description FROM items"
        cursor.execute(all_items_query)
        all_result = cursor.fetchall()
        #print(search_results)

        result_count = len(search_results)
        result_all = len(all_result)
        similarity = (result_count/result_all) * 100
        similarity = "{:.2f}".format(similarity)
        print(f'Similarity searching item is: {similarity} %')


        ## POSTREG
        #cursor = self.conn.cursor()
        #search_query = "SELECT id, description FROM items WHERE description LIKE %s"
        ## Execute the query with the parameter
        #cursor.execute(search_query, ('%' + query + '%',))
        #search_results = cursor.fetchall()
        #cursor.close()

        # Create the SearchItemsResponse message
        search_items_response = similarity_pb2.SearchItemsResponse()
        rows = []
        for row in search_results:
            item_id = row[0]
            rows.append(item_id)
        search_items_response.search_id = f'ID: {rows}'
        return search_items_response


    def GetSearchResults(self, request, context):
        search_id = request.search_id
        print(f'GetSearchResults, ID: {search_id}')

        # SQLite
        connection = self.get_connection()
        cursor = connection.cursor()
        # Execute the search query
        search_query = "SELECT id, description FROM items WHERE id = ?"
        cursor.execute(search_query, (search_id,))
        search_results = cursor.fetchall()

        ## POSTREG
        #cursor = self.conn.cursor()
        #search_query = "SELECT id, description FROM items WHERE id = 1"
        #cursor.execute(search_query, (search_id,))
        #search_results = cursor.fetchall()
        #cursor.close()

        # Convert search results to gRPC message format
        get_search_results_response = similarity_pb2.GetSearchResultsResponse()
        for result in search_results:
            search_result = get_search_results_response.results.add()
            search_result.id = str(result[0])
            search_result.description = result[1]

        return get_search_results_response




def serve():
    port = "50051"
    server = grpc.server(futures.ThreadPoolExecutor())
    similarity_pb2_grpc.add_SimilaritySearchServiceServicer_to_server(SimilaritySearchService(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

