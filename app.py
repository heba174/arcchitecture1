from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import bcrypt
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # مفتاح أمان الجلسات

# إعداد مجلد تحميل الصور
UPLOAD_FOLDER = 'static/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # إنشاء المجلد إذا لم يكن موجودًا
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# دالة لتشفير كلمة المرور
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# دالة للتحقق من كلمة المرور
def check_password(hashed_password, password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

# تهيئة قاعدة البيانات وإنشاء الجداول وإضافة المواد الأساسية
def init_db():
    with sqlite3.connect("db.sqlite3") as conn:
        cursor = conn.cursor()
        # تعديل الجدول لتخزين الصور المرتبطة بالمشاريع (إضافة العمود إذا لم يكن موجودًا)
    cursor.execute('''PRAGMA foreign_keys=OFF;''')  # تعطيل القيود المؤقتًا
    cursor.execute('''CREATE TABLE IF NOT EXISTS project_images (
                        id INTEGER PRIMARY KEY,
                        project_id INTEGER,
                        image_filename TEXT,
                        FOREIGN KEY (project_id) REFERENCES projects (id))''')
    cursor.execute('''PRAGMA foreign_keys=ON;''')  # تمكين القيود مرة أخرى

    # إنشاء جدول المواد إذا لم يكن موجودًا
    cursor.execute('''CREATE TABLE IF NOT EXISTS courses (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL)''')

    # إنشاء جدول المشاريع إذا لم يكن موجودًا
    cursor.execute('''CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY,
                        course_id INTEGER,
                        user_id INTEGER,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        FOREIGN KEY (course_id) REFERENCES courses (id),
                        FOREIGN KEY (user_id) REFERENCES users (id))''')

    # إنشاء جدول المستخدمين إذا لم يكن موجودًا
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL)''')

        # التحقق مما إذا كانت المواد قد تمت إضافتها من قبل
    cursor.execute("SELECT COUNT(*) FROM courses")
    course_count = cursor.fetchone()[0]
        
    if course_count == 0:  # إضافة المواد فقط إذا لم تكن موجودة بالفعل
            courses = [
                ("مقدمة في العمارة", "تعريف بأسس ومبادئ العمارة."),
                ("تاريخ العمارة", "دراسة تاريخ العمارة العالمية وتطورها."),
                ("تصميم معماري", "مقدمة حول التصميم المعماري وأساليبه."),
                ("الرسومات المعمارية", "تعلم الرسومات المعمارية والبرامج المستخدمة.")
            ]
            for name, description in courses:
                cursor.execute("INSERT INTO courses (name, description) VALUES (?, ?)", (name, description))
        
        # إضافة مستخدم مسؤول افتراضي
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                       ('admin', hash_password('adminpass'), 'admin'))
    conn.commit()

init_db()


# تعريف كلاس User للتعامل مع المستخدمين
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect("db.sqlite3") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
    if user:
        return User(id=user[0], username=user[1], role=user[3])
    return None

# صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect("db.sqlite3") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
        if user and check_password(user[2], password):
            login_user(User(id=user[0], username=user[1], role=user[3]))
            flash("تم تسجيل الدخول بنجاح!", "success")
            return redirect(url_for('index'))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")
    return render_template('login.html')

# صفحة تسجيل الخروج
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج بنجاح!", "info")
    return redirect(url_for('index'))

# الصفحة الرئيسية - قائمة المواد
@app.route('/', methods=['GET', 'POST'])
def index():
    search_query = request.args.get('search', '')  # جلب النص الذي يبحث عنه المستخدم
    with sqlite3.connect("db.sqlite3") as conn:
        cursor = conn.cursor()
        
        if search_query:
            # تنفيذ استعلام للبحث عن المواد بناءً على النص المدخل في الاسم أو الوصف
            cursor.execute("SELECT * FROM courses WHERE name LIKE ? OR description LIKE ?", ('%' + search_query + '%', '%' + search_query + '%'))
        else:
            # إذا لم يكن هناك نص للبحث، نقوم بجلب جميع المواد
            cursor.execute("SELECT * FROM courses")
        
        courses = cursor.fetchall()
    
    return render_template('index.html', courses=courses)
# إضافة صفحة البحث في app.py
@app.route('/search')
def search():
    query = request.args.get('query')
    if query:
        with sqlite3.connect("db.sqlite3") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM courses WHERE name LIKE ?", ('%' + query + '%',))
            courses = cursor.fetchall()
        
        # إرسال النتائج على شكل JSON
        return jsonify({'courses': [{'name': course[1], 'description': course[2]} for course in courses]})
    else:
        return jsonify({'courses': []})  # إذا لم يكن هناك استعلام، يتم إرجاع قائمة فارغة


# صفحة تعريف المادة
@app.route('/course/<int:course_id>')
def course(course_id):
    with sqlite3.connect("db.sqlite3") as conn:
        cursor = conn.cursor()

        # استرجاع تفاصيل المادة بناءً على ID المادة
        cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        course = cursor.fetchone()

        # استرجاع المشاريع مع جميع الصور المرتبطة بكل مشروع
        cursor.execute('''
            SELECT projects.id, projects.name, projects.description, users.username,projects.user_id, project_images.image_filename
            FROM projects
            JOIN users ON projects.user_id = users.id
            LEFT JOIN project_images ON projects.id = project_images.project_id
            WHERE projects.course_id = ?
        ''', (course_id,))

        projects = cursor.fetchall()

        # تنظيم البيانات بحيث يتم جمع الصور مع المشروع
        project_data = {}
        for project in projects:
            project_id = project[0]
            if project_id not in project_data:
                project_data[project_id] = {
                    'name': project[1],
                    'description': project[2],
                    'username': project[3],
                     'user_id': project[4],        # user_id
                    'images': []
                }
            if project[5]:  # تأكد من وجود اسم الصورة
                project_data[project_id]['images'].append(project[5])

    return render_template('course.html', course=course, projects=project_data)







# إضافة مشروع جديد - تتطلب تسجيل الدخول
@app.route('/course/<int:course_id>/add_project', methods=['GET', 'POST'])
@login_required
def add_project(course_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']

        # تحميل الصور
        image_files = request.files.getlist('images')  # الحصول على كل الصور المرفوعة
        image_paths = []

        # حفظ كل صورة في المجلد
        for image_file in image_files:
            if image_file:
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
                image_paths.append(filename)  # تخزين اسم الصورة

        with sqlite3.connect("db.sqlite3") as conn:
            cursor = conn.cursor()

            # إدخال المشروع في جدول المشاريع
            cursor.execute("INSERT INTO projects (course_id, user_id, name, description) VALUES (?, ?, ?, ?) ",
                           (course_id, current_user.id, name, description))
            project_id = cursor.lastrowid  # الحصول على ID المشروع المضاف

            # إدخال أسماء الصور المرتبطة بالمشروع
            for image in image_paths:
                cursor.execute("INSERT INTO project_images (project_id, image_filename) VALUES (?, ?)",
                               (project_id, image))
            
            conn.commit()
        
        flash("تم إضافة المشروع والصور بنجاح!", "success")
        return redirect(url_for('course', course_id=course_id))

    return render_template('add_project.html', course_id=course_id)

#حذف مشروع
@app.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    with sqlite3.connect("db.sqlite3") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()

        # تحقق إذا كان المشروع ينتمي للمستخدم الحالي
        if project and project[2] == current_user.id:
            # حذف الصور المرتبطة بالمشروع أولاً
            cursor.execute("SELECT image_filename FROM project_images WHERE project_id = ?", (project_id,))
            images = cursor.fetchall()
            for image in images:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image[0])
                if os.path.exists(image_path):
                    os.remove(image_path)  # حذف الصورة من المجلد

            # حذف المشروع من جدول المشاريع
            cursor.execute("DELETE FROM project_images WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

            flash("تم حذف المشروع بنجاح!", "success")

    # إعادة تحميل الصفحة الحالية بدلاً من التوجيه إلى صفحة أخرى
    return redirect(url_for('course', course_id=project[1]))




# إضافة طالب جديد (للمسؤولين فقط)
@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.role != 'admin':
        flash("غير مسموح لك بالوصول إلى هذه الصفحة.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        action = request.form['action']  # تحديد ما إذا كان الفعل إضافة أو حذف
        
        # إذا كان الفعل هو إضافة طالب
        if action == 'add':
            hashed_password = hash_password(password)
            with sqlite3.connect("db.sqlite3") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, 'student'))
                conn.commit()
            flash("تم إضافة الطالب بنجاح!", "success")

        # إذا كان الفعل هو حذف طالب
        elif action == 'delete':
            with sqlite3.connect("db.sqlite3") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                student = cursor.fetchone()

                if student and check_password(student[2], password):  # التحقق من كلمة المرور
                    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                    conn.commit()
                    flash("تم حذف الطالب بنجاح!", "success")
                else:
                    flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")

        return redirect(url_for('add_student'))

    return render_template('add_student.html')
@app.route('/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
   
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        action = request.form['action']

        if action == 'add':
            with sqlite3.connect("db.sqlite3") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO courses (name, description) VALUES (?, ?)", (name, description))
                conn.commit()
            flash("تمت إضافة المادة بنجاح!", "success")

        elif action == 'delete':
            with sqlite3.connect("db.sqlite3") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM courses WHERE name = ?", (name,))
                conn.commit()
            flash("تم حذف المادة بنجاح!", "success")

        return redirect(url_for('index'))

    return render_template('add_course.html')


if __name__ == '__main__':
    app.run(debug=True)


