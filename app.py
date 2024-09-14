from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import uuid
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB 설정
client = MongoClient('mongodb://localhost:27017/')
db = client['travel_records']
collection = db['posts']

# 파일 업로드 설정
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



def allowed_file(filename):
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in ALLOWED_EXTENSIONS
    return False

def generate_unique_filename(filename):
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
    else:
        flash('파일 이름에 확장자가 없습니다.')
        return None
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return unique_filename


@app.route('/write', methods=['GET', 'POST'])                               # write
def write():
    if request.method == 'POST':
        return redirect(url_for('upload'))
    return render_template('write.html')

@app.route('/upload', methods=['POST'])
def upload():
    content = request.form.get('content', '')

    # 폼 데이터에서 태그 가져오기
    age = request.form.get('age','나이대')
    gender = request.form.get('gender', '성별')
    travel_type = request.form.get('travel_type', '여행 유형')
    region = request.form.get('region', '지역')
    cost = request.form.get('cost', '비용')
    relationship = request.form.get('relationship', '관계')

    tags = {
        'age': age,
        'gender': gender,
        'travel_type': travel_type,
        'region': region,
        'cost': cost,
        'relationship': relationship
    }

    print("Received tags:", tags)

    if 'file' not in request.files:
        flash('파일이 선택되지 않았습니다.')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('선택된 파일이 없습니다.')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(filename)
        
        if unique_filename is None:
            return redirect(request.url)  # 확장자가 없으면 업로드를 중단하고 리다이렉트
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(file_path)
            flash(f"파일이 성공적으로 저장되었습니다: {file_path}")
        except Exception as e:
            flash(f"파일 저장 중 오류 발생: {str(e)}")
            return redirect(request.url)

        post_data = {
            'content': content,
            'image_path': file_path,
            'tags': tags
        }

        try:
            collection.insert_one(post_data)
            flash('글이 업로드되었습니다.')
        except Exception as e:
            flash(f"MongoDB 저장 중 오류 발생: {str(e)}")
            print(f"MongoDB 저장 중 오류: {str(e)}")
            return redirect(request.url)
        
        return redirect(url_for('write'))
    
    flash('허용되지 않는 파일 형식입니다.')
    return redirect(request.url)

@app.route('/add', methods=['POST'])
def add_document():
    data = request.json
    collection.insert_one(data)
    return jsonify({"message": "Document added!"}), 201

@app.route('/documents', methods=['GET'])
def get_documents():
    documents = list(collection.find({}, {"_id": 0}))  # MongoDB에서 문서를 가져오고, _id 필드 제외
    return jsonify(documents), 200

@app.route('/post/<post_id>')                                                 # post
def post(post_id):
    post_data = collection.find_one({'_id': ObjectId(post_id)})

    if not post_data:
        return "No posts found", 404
    
    user_id = "exampleUserId"  # 실제 로그인된 사용자 ID로 대체

    #MongoDB에서 가져온 데이터를 템플릿에 전달할수 있는 형태로 변환
    post_data['username'] = post_data.get('username', 'Anonymous')
    post_data['location'] = post_data.get('location', 'Unknown')
    post_data['post_content'] = post_data.get('content', '')
    post_data['tags'] = list(post_data.get('tags', {}).values())
    post_data['comments'] = post_data.get('comments',[]) #댓글에 데이터 추가
    post_data['likes'] = post_data.get('likes',0) #좋아요 수 추가
    post_data['like_by_user'] = user_id in post_data.get('like_by', [])

    # 이미지 데이터는 파일 경로를 전달하거나 base64로 인코딩하여 전달할 수 있습니다.
    with open(post_data['image_path'], "rb") as image_file:
        image_data = image_file.read()
        image_data_base64 = base64.b64encode(image_data).decode('utf-8')

    post_data['image_data'] = image_data_base64
    post_data['image_filename'] = os.path.basename(post_data['image_path'])

    return render_template('post.html', post=post_data)

@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.args.get('query', '')  # 검색어를 가져옵니다. 기본값은 빈 문자열
    print(f"검색어: {query}")  # 검색어를 출력하여 확인
    
    if query:
        # 검색어와 태그가 일치하는 포스트를 필터링합니다.
        posts = list(collection.find({"tags": {"$regex": query, "$options": "i"}}))
        print(f"필터링된 포스트 개수: {len(posts)}")  # 필터링된 결과의 개수 출력
    else:
        # 검색어가 없을 경우 모든 포스트를 가져옵니다.
        posts = list(collection.find())
        print(f"모든 포스트 개수: {len(posts)}")  # 전체 결과의 개수 출력

    # 각 포스트의 이미지 데이터를 base64로 인코딩합니다.
    for post in posts:
        with open(post['image_path'], "rb") as image_file:
            image_data = image_file.read()
            post['image_data'] = base64.b64encode(image_data).decode('utf-8')
        
        # 템플릿에서 사용하기 쉽게 데이터 변환
        post['username'] = post.get('username', 'Anonymous')
        post['location'] = post.get('location', 'Unknown')
        post['post_content'] = post.get('content', '')
        post['tags'] = list(post.get('tags', {}).values())

    user_name = "YourUserName"
    return render_template('search.html', posts=posts, user_name=user_name)


@app.route('/add_comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    comment_text = request.form['comment']


    username = session.get('username','익명')
    # 댓글을 MongoDB에 추가
    collection.update_one(
        {'_id': ObjectId(post_id)},
        {'$push': {'comments': {'username': username, 'text': comment_text}}}
    )

    return redirect(url_for('post', post_id=post_id))

@app.route('/like/<post_id>', methods=['POST'])
def like(post_id):
    user_id = request.form.get('user_id')  # 예를 들어 사용자 ID를 폼 데이터에서 가져옴

    # 해당 포스트 데이터를 가져옵니다.
    post_data = collection.find_one({'_id': ObjectId(post_id)})

    if not post_data:
        return jsonify({'error': 'Post not found'}), 404

    if 'liked_by' not in post_data:
        post_data['liked_by'] = []

    if user_id in post_data['liked_by']:
        # 이미 좋아요를 눌렀다면, 좋아요 취소
        collection.update_one(
            {'_id': ObjectId(post_id)},
            {'$inc': {'likes': -1}, '$pull': {'liked_by': user_id}}
        )
        new_like_status = False
    else:
        # 좋아요를 누르지 않았다면, 좋아요 추가
        collection.update_one(
            {'_id': ObjectId(post_id)},
            {'$inc': {'likes': 1}, '$push': {'liked_by': user_id}}
        )
        new_like_status = True

    # 업데이트된 포스트 데이터를 다시 가져옵니다.
    updated_post = collection.find_one({'_id': ObjectId(post_id)})

    return jsonify({
        'likes': updated_post.get('likes', 0),
        'liked_by_user': new_like_status
    })


# @app.route('/save_post/<post_id>', methods=['POST'])
# def save_post(post_id):
#     post_data = collection.find_one({'_id': ObjectId(post_id)})

#     if not post_data:
#         return jsonify({'error': 'Post not found'}), 404

#     # 게시물의 `saved` 상태를 True로 설정
#     collection.update_one(
#         {'_id': ObjectId(post_id)},
#         {'$set': {'saved': True}}
#     )

#     return jsonify({'saved': True})


@app.route('/save_post/<post_id>', methods=['POST'])
def save_post(post_id):
    post_data = collection.find_one({'_id': ObjectId(post_id)})

    if not post_data:
        return jsonify({'error': 'Post not found'}), 404

    # 게시물의 현재 saved 상태를 확인
    current_saved_status = post_data.get('saved', False)

    # 현재 상태와 반대로 설정
    new_saved_status = not current_saved_status

    # MongoDB 문서 업데이트
    collection.update_one(
        {'_id': ObjectId(post_id)},
        {'$set': {'saved': new_saved_status}}
    )

    return jsonify({'saved': new_saved_status})




@app.route('/save')
def save_posts():
        # 저장된 게시물만 필터링하여 가져오기
    saved_posts = list(collection.find({'saved': True}))

    # 각 게시물의 이미지 데이터를 base64로 인코딩하여 템플릿에 전달
    for post in saved_posts:
        with open(post['image_path'], "rb") as image_file:
            image_data = image_file.read()
            post['image_data'] = base64.b64encode(image_data).decode('utf-8')

    # if not user or 'saved_posts' not in user:
    #     saved_posts = []
    # else:
    #     # ObjectId 목록을 사용하여 저장된 게시물들을 가져옵니다.
    #     saved_posts = list(collection.find({'_id': {'$in': [ObjectId(post_id) for post_id in user['saved_posts']]}}))

    #     # 각 게시물의 이미지 데이터를 base64로 인코딩하여 템플릿에 전달
    #     for post in saved_posts:
    #         with open(post['image_path'], "rb") as image_file:
    #             image_data = image_file.read()
    #             post['image_data'] = base64.b64encode(image_data).decode('utf-8')

    return render_template('save.html',posts = saved_posts )








@app.route('/search', methods=['GET'])
def searchpost():
    query = request.args.get('query', '').strip()  # 검색어를 가져옵니다.

    if query:
        # 태그의 값 중에 검색어가 포함된 포스트를 찾습니다.
        posts = list(collection.find({"tags": {"$regex": query, "$options": "i"}}))
    else:
        # 검색어가 없을 경우 모든 포스트를 가져옵니다.
        posts = list(collection.find())

    # 각 포스트의 이미지 데이터를 base64로 인코딩합니다.
    for post in posts:
        with open(post['image_path'], "rb") as image_file:
            image_data = image_file.read()
            post['image_data'] = base64.b64encode(image_data).decode('utf-8')
        
        # 템플릿에서 사용하기 쉽게 데이터 변환
        post['username'] = post.get('username', 'Anonymous')
        post['location'] = post.get('location', 'Unknown')
        post['post_content'] = post.get('content', '')
        post['tags'] = list(post.get('tags', {}).values())

    user_name = session.get('username', '익명')  # 사용자 이름을 세션에서 가져옵니다.
    return render_template('search.html', posts=posts, user_name=user_name)




@app.route('/home')
def home():
    # 홈 페이지에 대한 로직을 추가
    return render_template('home.html', username=session.get('username'))

@app.route('/my')
def my():
    # 사용자 개인 페이지에 대한 로직 추가
    return render_template('my.html')

@app.route('/setting')
def setting():
    # 설정 페이지에 대한 로직 추가
    return render_template('setting.html')


# @app.route('/search')
# def search():
#     posts = list(collection.find({}, {"_id": 0}))  # 모든 게시물 가져오기, _id 필드 제외
#     return render_template('search.html', posts=posts)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)





###