from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import ObjectId
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

@app.route('/')

@app.route('/write', methods=['GET', 'POST'])
def write():
    popular_tags = {
        'age': get_most_common_tag_value('age'),
        'gender': get_most_common_tag_value('gender'),
        'travel_type': get_most_common_tag_value('travel_type'),
        'region': get_most_common_tag_value('region'),
        'cost': get_most_common_tag_value('cost'),
        'relationship': get_most_common_tag_value('relationship'),
    }

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        travel_type = request.form.get('travel_type', '').strip()
        region = request.form.get('region', '').strip()
        cost = request.form.get('cost', '').strip()
        relationship = request.form.get('relationship', '').strip()

        tags = {
            'age': age,
            'gender': gender,
            'travel_type': travel_type,
            'region': region,
            'cost': cost,
            'relationship': relationship
        }

        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = generate_unique_filename(filename)
            if unique_filename:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                post_data = {
                    'content': content,
                    'image_path': f"uploads/{unique_filename}",
                    'tags': tags
                }
                collection.insert_one(post_data)
                flash('글이 업로드되었습니다.')
                return redirect(url_for('write'))
            else:
                return redirect(url_for('write'))
        else:
            flash('허용되지 않는 파일 형식입니다.')
            return redirect(url_for('write'))

    return render_template('write.html', popular_tags=popular_tags)

@app.route('/upload', methods=['POST'])
def upload():
    content = request.form.get('content', '')

    # 폼 데이터에서 태그 가져오기
    age = request.form.get('age', '나이대')
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

    print(value for value in tags.values())
    print(content)
    print("Received tags:", tags)

    # 필수 필드가 비어있으면 업로드 중단 및 사용자에게 알림
    missing_fields = []
    # 태그 중 하나라도 '미선택'이 아닌 경우에만 업로드를 허용
    if age == '미선택':
        missing_fields.append('나이대')
    if gender == '미선택':
        missing_fields.append('성별')
    if travel_type == '미선택':
        missing_fields.append('여행 유형')
    if region == '미선택':
        missing_fields.append('지역')
    if cost == '미선택':
        missing_fields.append('비용')
    if relationship == '미선택':
        missing_fields.append('관계')

    if missing_fields:
        if 'file' not in request.files or request.files['file'].filename == '':
            flash(f"다음 항목들이 채워주세요: 사진, 관심사({', '.join(missing_fields)})")
        else:
            flash(f"다음 항목들이 채워주세요: 관심사({', '.join(missing_fields)})")
        return redirect(request.url)
    else:
        if 'file' not in request.files or request.files['file'].filename == '':
            flash("다음 항목들이 채워주세요: 사진")
            return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('사진을 올려주세요.')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(filename)

        if unique_filename is None:
            return redirect(request.url)  # 확장자가 없으면 업로드를 중단하고 리다이렉트

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        try:
            file.save(file_path)
            flash("글이 업로드 되었습니다.")
        except Exception as e:
            flash(f"파일 저장 중 오류 발생: {str(e)}")
            return redirect(request.url)

        post_data = {
            'content': content,
            'image_path': f"uploads/{unique_filename}",
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

@app.route('/upload', methods=['GET'])
def upload_get():
    return redirect(url_for('write'))

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    selected_region = request.json.get('region')

    if selected_region:
        pipeline = [
            {"$match": {"tags.region": selected_region}},  # 지역 필터링
            {"$sample": {"size": 2}}  # 무작위로 2개 선택
        ]
        posts = list(collection.aggregate(pipeline))

        for post in posts:
            post['_id'] = str(post['_id'])  # ObjectId를 문자열로 변환
            post['image_path'] = url_for('static', filename=post['image_path'])  # 이미지 경로 처리

        return jsonify({"posts": posts})

    return jsonify({"posts": []}), 404

def get_most_common_tag_value(tag_name):
    pipeline = [
        {"$group": {"_id": f"$tags.{tag_name}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    result = list(collection.aggregate(pipeline))
    if result:
        return result[0]['_id']
    else:
        return "미선택"

@app.route('/add', methods=['POST'])
def add_document():
    data = request.json
    collection.insert_one(data)
    return jsonify({"message": "Document added!"}), 201

@app.route('/documents', methods=['GET'])
def get_documents():
    documents = list(collection.find({}, {"_id": 0}))  # MongoDB에서 문서를 가져오고, _id 필드 제외
    return jsonify(documents), 200

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
def save():
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

@app.route('/my')
def my():
    # MongoDB에서 최신 두 개의 게시물 데이터를 가져옵니다.
    posts = list(collection.find().sort('_id', -1).limit(2))  # 최신 두 개의 게시물만 가져오기

    # 데이터의 _id 필드를 문자열로 변환합니다 (Flask에서 다루기 쉽게 하기 위함)
    for post in posts:
        post['_id'] = str(post['_id'])
    # 나의 여행 페이지 렌더링
    return render_template('my.html', posts=posts)

@app.route('/deco')
def deco():
    # 나의 악세사리 페이지 렌더링
    return render_template('deco.html')

@app.route('/badge')
def badge():
    # 나의 뱃지 페이지 렌더링
    return render_template('badge.html')


@app.route('/mypost')
def mypost():
    # MongoDB에서 모든 게시물 데이터를 가져옵니다.
    posts = list(collection.find())

    # 데이터의 _id 필드를 문자열로 변환합니다 (Flask에서 다루기 쉽게 하기 위함)
    for post in posts:
        post['_id'] = str(post['_id'])

    return render_template('mypost.html', posts=posts)

@app.route('/mypost/<post_id>')
def view_mypost(post_id):
    post = collection.find_one({"_id": ObjectId(post_id)})

    if not post:
        return "Post not found", 404

    # 디버깅용 출력
    print("Post content:", post.get('post_content'))

    # 이미지 파일 경로에서 base64 인코딩된 이미지 데이터를 생성
    image_path = os.path.join('static', post['image_path'])  # 'static'과 이미지 경로를 연결

    if not os.path.exists(image_path):
        return "Image not found", 404

    with open(image_path, "rb") as image_file:
        post['image_data'] = base64.b64encode(image_file.read()).decode('utf-8')

    return render_template('myPostDetail.html', post=post)

@app.route('/add_comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    comment_text = request.form['comment']


    username = session.get('username', '익명')
    # 댓글을 MongoDB에 추가
    collection.update_one(
        {'_id': ObjectId(post_id)},
        {'$push': {'comments': {'username': username, 'text': comment_text}}}
    )

    return redirect(url_for('view_mypost', post_id=post_id))

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

@app.route('/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    try:
        # MongoDB에서 해당 게시물 삭제
        result = collection.delete_one({'_id': ObjectId(post_id)})
        if result.deleted_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': '삭제할 게시물을 찾을 수 없습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'게시물 삭제 중 오류 발생: {str(e)}'})


    # 게시물 목록 페이지로 리다이렉트
    return redirect(url_for('mypost'))

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

@app.route('/search', methods=['GET'])
def searchpost():
    query = request.args.get('query', '').strip()  # 검색어를 가져옵니다.
    print(f"Received query: {query}")  # 디버그용으로 쿼리 출력

    if query:
        # 각 태그 필드에 대해 검색어가 포함된 포스트를 찾습니다.
        posts = list(collection.find({
            "$or": [
                {"tags.age": {"$regex": query, "$options": "i"}},
                {"tags.gender": {"$regex": query, "$options": "i"}},
                {"tags.travel_type": {"$regex": query, "$options": "i"}},
                {"tags.region": {"$regex": query, "$options": "i"}},
                {"tags.cost": {"$regex": query, "$options": "i"}},
                {"tags.relationship": {"$regex": query, "$options": "i"}}
            ]
        }))
        print(f"Found posts: {len(posts)}")

    else:
        # 검색어가 없을 경우 모든 포스트를 가져옵니다.
        posts = list(collection.find())
        print(f"Found posts without query: {len(posts)}")

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

@app.route('/setting')
def setting():
    # 설정 페이지에 대한 로직 추가
    return render_template('setting.html')

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
