### FOR DEPLOYMENT ###

from flask import Flask, request, jsonify, Response, stream_template
from service.llm_service import process_news_request, get_company_profile
import threading
import uuid
import json

app = Flask(__name__)

news_progress = {}
progress_lock = threading.Lock()

@app.route('/ai-news/news', methods=['POST'])
def get_company_news():
    data = request.json
    company = data.get('company', 'AI')
    time_option = data.get('time_option', 'this_week')
    max_items = data.get('max_items', 10)

    # Check if user wants streaming (single request) or polling
    use_streaming = data.get('streaming', True)  # Default to streaming

    if use_streaming:
        # Single request - process everything and return result directly
        try:
            from llm_news.llm_news_scraper import get_news_with_summary
            result = get_news_with_summary(company, time_option, max_items)
            return jsonify({
                'status': 'complete',
                'result': result,
                'streaming': True
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e),
                'streaming': True
            }), 500
    else:
        # Fallback to polling for compatibility
        session_id = str(uuid.uuid4())

        with progress_lock:
            news_progress[session_id] = {
                'status': 'starting',
                'message': 'Initializing search...',
                'articles': [],
                'total': 0,
                'processed': 0,
                'complete': False,
                'result': None
            }

        from llm_news.llm_news_scraper import get_news_with_summary_tracked

        def process_news():
            try:
                result = get_news_with_summary_tracked(company, time_option, max_items, session_id, news_progress)
                with progress_lock:
                    news_progress[session_id]['result'] = result
                    news_progress[session_id]['status'] = 'complete'
            except Exception as e:
                with progress_lock:
                    news_progress[session_id]['status'] = 'error'
                    news_progress[session_id]['message'] = str(e)
            finally:
                with progress_lock:
                    news_progress[session_id]['complete'] = True

        thread = threading.Thread(target=process_news)
        thread.start()

        return jsonify({'session_id': session_id, 'streaming': False}), 202

@app.route('/ai-news/progress/<session_id>', methods=['GET'])
def get_progress(session_id):
    with progress_lock:
        if session_id not in news_progress:
            return jsonify({'error': 'Invalid session ID'}), 404

        progress = news_progress[session_id].copy()

    if progress['complete']:
        threading.Timer(300.0, lambda: cleanup_session(session_id)).start()
        return jsonify(progress)

    return jsonify(progress)

@app.route('/ai-news/news/stream', methods=['POST'])
def get_company_news_stream():
    """SSE endpoint for streaming news updates with real-time progress bar"""
    data = request.json
    company = data.get('company', 'AI')
    time_option = data.get('time_option', 'this_week')
    max_items = data.get('max_items', 10)

    session_id = str(uuid.uuid4())

    def generate():
        """Generate SSE events with real-time progress updates"""
        try:
            # Initialize progress
            with progress_lock:
                news_progress[session_id] = {
                    'status': 'starting',
                    'message': 'Initializing search...',
                    'articles': [],
                    'total': 0,
                    'processed': 0,
                    'complete': False,
                    'result': None
                }

            # Send initial event immediately
            yield f"data: {json.dumps({'event': 'progress', 'data': json.dumps({'status': 'starting', 'message': 'Initializing search...', 'articles': [], 'total': 0, 'processed': 0})})}\n\n"

            from llm_news.llm_news_scraper import get_news_with_summary_tracked

            # Process news in background thread and monitor progress
            def process_news():
                try:
                    result = get_news_with_summary_tracked(company, time_option, max_items, session_id, news_progress)
                    with progress_lock:
                        news_progress[session_id]['result'] = result
                        news_progress[session_id]['status'] = 'complete'
                        news_progress[session_id]['complete'] = True
                except Exception as e:
                    with progress_lock:
                        news_progress[session_id]['status'] = 'error'
                        news_progress[session_id]['message'] = str(e)
                        news_progress[session_id]['complete'] = True

            thread = threading.Thread(target=process_news)
            thread.start()

            # Set up event queue for real-time article updates
            event_queue = []
            
            def send_sse_event(event_type, data):
                """Queue SSE event for immediate sending"""
                event_data = {
                    'event': event_type,
                    'data': json.dumps(data)
                }
                event_queue.append(f"data: {json.dumps(event_data)}\n\n")
            
            # Store a reference to the event queue in progress dict for article processing
            with progress_lock:
                news_progress[session_id]['_event_queue'] = event_queue
            
            # Monitor progress and send SSE events immediately
            last_progress = None
            while True:
                # Send any queued events first
                while event_queue:
                    yield event_queue.pop(0)
                
                with progress_lock:
                    progress = news_progress[session_id].copy()
                    # Remove non-serializable items from progress
                    if '_event_queue' in progress:
                        del progress['_event_queue']
                
                # Only send if progress has changed
                if last_progress != progress:
                    # Send progress update immediately
                    yield f"data: {json.dumps({'event': 'progress', 'data': json.dumps(progress)})}\n\n"
                    last_progress = progress
                
                # Check if complete
                if progress.get('complete', False):
                    if progress.get('status') == 'complete' and progress.get('result'):
                        yield f"data: {json.dumps({'event': 'complete', 'data': json.dumps({'status': 'complete', 'message': 'Search complete', 'result': progress['result']})})}\n\n"
                    else:
                        yield f"data: {json.dumps({'event': 'error', 'data': json.dumps({'status': 'error', 'message': progress.get('message', 'Unknown error'), 'complete': True})})}\n\n"
                    break
                
                # Wait before next check
                import time
                time.sleep(0.3)  # Faster updates for better progress bar

        except Exception as e:
            # Send error event immediately
            yield f"data: {json.dumps({'event': 'error', 'data': json.dumps({'status': 'error', 'message': str(e), 'complete': True})})}\n\n"
        finally:
            # Cleanup session after 5 minutes
            threading.Timer(300.0, lambda: cleanup_session(session_id)).start()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

def cleanup_session(session_id):
    with progress_lock:
        news_progress.pop(session_id, None)

@app.route('/ai-news/company_profile', methods=['GET'])
def company_profile():
    company = request.args.get('company')
    result = get_company_profile(company)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100, debug=False, threaded=True)

### LOCAL TESTING ###
# from flask import Flask, request, jsonify, Response, stream_template
# from service.llm_service import process_news_request, get_company_profile
# import threading
# import uuid
# import json

# app = Flask(__name__)

# news_progress = {}
# progress_lock = threading.Lock()

# @app.route('/ai-news/news', methods=['POST'])
# def get_company_news():
#     data = request.json
#     company = data.get('company', 'AI')
#     time_option = data.get('time_option', 'this_week')
#     max_items = data.get('max_items', 10)

#     # Check if user wants streaming (single request) or polling
#     use_streaming = data.get('streaming', True)  # Default to streaming

#     if use_streaming:
#         # Single request - process everything and return result directly
#         try:
#             from llm_news.llm_news_scraper import get_news_with_summary
#             result = get_news_with_summary(company, time_option, max_items)
#             return jsonify({
#                 'status': 'complete',
#                 'result': result,
#                 'streaming': True
#             })
#         except Exception as e:
#             return jsonify({
#                 'status': 'error',
#                 'message': str(e),
#                 'streaming': True
#             }), 500
#     else:
#         # Fallback to polling for compatibility
#         session_id = str(uuid.uuid4())

#         with progress_lock:
#             news_progress[session_id] = {
#                 'status': 'starting',
#                 'message': 'Initializing search...',
#                 'articles': [],
#                 'total': 0,
#                 'processed': 0,
#                 'complete': False,
#                 'result': None
#             }

#         from llm_news.llm_news_scraper import get_news_with_summary_tracked

#         def process_news():
#             try:
#                 result = get_news_with_summary_tracked(company, time_option, max_items, session_id, news_progress)
#                 with progress_lock:
#                     news_progress[session_id]['result'] = result
#                     news_progress[session_id]['status'] = 'complete'
#             except Exception as e:
#                 with progress_lock:
#                     news_progress[session_id]['status'] = 'error'
#                     news_progress[session_id]['message'] = str(e)
#             finally:
#                 with progress_lock:
#                     news_progress[session_id]['complete'] = True

#         thread = threading.Thread(target=process_news)
#         thread.start()

#         return jsonify({'session_id': session_id, 'streaming': False}), 202

# @app.route('/ai-news/progress/<session_id>', methods=['GET'])
# def get_progress(session_id):
#     with progress_lock:
#         if session_id not in news_progress:
#             return jsonify({'error': 'Invalid session ID'}), 404

#         progress = news_progress[session_id].copy()

#     if progress['complete']:
#         threading.Timer(300.0, lambda: cleanup_session(session_id)).start()
#         return jsonify(progress)

#     return jsonify(progress)

# @app.route('/ai-news/news/stream', methods=['POST'])
# def get_company_news_stream():
#     """SSE endpoint for streaming news updates with real-time progress bar"""
#     data = request.json
#     company = data.get('company', 'AI')
#     time_option = data.get('time_option', 'this_week')
#     max_items = data.get('max_items', 10)

#     session_id = str(uuid.uuid4())

#     def generate():
#         """Generate SSE events with real-time progress updates"""
#         try:
#             # Initialize progress
#             with progress_lock:
#                 news_progress[session_id] = {
#                     'status': 'starting',
#                     'message': 'Initializing search...',
#                     'articles': [],
#                     'total': 0,
#                     'processed': 0,
#                     'complete': False,
#                     'result': None
#                 }

#             # Send initial event immediately
#             yield f"data: {json.dumps({'event': 'progress', 'data': json.dumps({'status': 'starting', 'message': 'Initializing search...', 'articles': [], 'total': 0, 'processed': 0})})}\n\n"

#             from llm_news.llm_news_scraper import get_news_with_summary_tracked

#             # Process news in background thread and monitor progress
#             def process_news():
#                 try:
#                     result = get_news_with_summary_tracked(company, time_option, max_items, session_id, news_progress)
#                     with progress_lock:
#                         news_progress[session_id]['result'] = result
#                         news_progress[session_id]['status'] = 'complete'
#                         news_progress[session_id]['complete'] = True
#                 except Exception as e:
#                     with progress_lock:
#                         news_progress[session_id]['status'] = 'error'
#                         news_progress[session_id]['message'] = str(e)
#                         news_progress[session_id]['complete'] = True

#             thread = threading.Thread(target=process_news)
#             thread.start()

#             # Set up event queue for real-time article updates
#             event_queue = []
            
#             def send_sse_event(event_type, data):
#                 """Queue SSE event for immediate sending"""
#                 event_data = {
#                     'event': event_type,
#                     'data': json.dumps(data)
#                 }
#                 event_queue.append(f"data: {json.dumps(event_data)}\n\n")
            
#             # Store a reference to the event queue in progress dict for article processing
#             with progress_lock:
#                 news_progress[session_id]['_event_queue'] = event_queue
            
#             # Monitor progress and send SSE events immediately
#             last_progress = None
#             while True:
#                 # Send any queued events first
#                 while event_queue:
#                     yield event_queue.pop(0)
                
#                 with progress_lock:
#                     progress = news_progress[session_id].copy()
#                     # Remove non-serializable items from progress
#                     if '_event_queue' in progress:
#                         del progress['_event_queue']
                
#                 # Only send if progress has changed
#                 if last_progress != progress:
#                     # Send progress update immediately
#                     yield f"data: {json.dumps({'event': 'progress', 'data': json.dumps(progress)})}\n\n"
#                     last_progress = progress
                
#                 # Check if complete
#                 if progress.get('complete', False):
#                     if progress.get('status') == 'complete' and progress.get('result'):
#                         yield f"data: {json.dumps({'event': 'complete', 'data': json.dumps({'status': 'complete', 'message': 'Search complete', 'result': progress['result']})})}\n\n"
#                     else:
#                         yield f"data: {json.dumps({'event': 'error', 'data': json.dumps({'status': 'error', 'message': progress.get('message', 'Unknown error'), 'complete': True})})}\n\n"
#                     break
                
#                 # Wait before next check
#                 import time
#                 time.sleep(0.3)  # Faster updates for better progress bar

#         except Exception as e:
#             # Send error event immediately
#             yield f"data: {json.dumps({'event': 'error', 'data': json.dumps({'status': 'error', 'message': str(e), 'complete': True})})}\n\n"
#         finally:
#             # Cleanup session after 5 minutes
#             threading.Timer(300.0, lambda: cleanup_session(session_id)).start()

#     return Response(
#         generate(),
#         mimetype='text/event-stream',
#         headers={
#             'Cache-Control': 'no-cache',
#             'Connection': 'keep-alive',
#             'Access-Control-Allow-Origin': '*',
#             'Access-Control-Allow-Headers': 'Cache-Control'
#         }
#     )

# def cleanup_session(session_id):
#     with progress_lock:
#         news_progress.pop(session_id, None)

# @app.route('/ai-news/company_profile', methods=['GET'])
# def company_profile():
#     company = request.args.get('company')
#     result = get_company_profile(company)
#     return jsonify(result)

# @app.after_request
# def after_request(response):
#     response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
#     response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
#     response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
#     return response

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5100, debug=True) 

