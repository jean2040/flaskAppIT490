import pika
from rpc_pub import RpcPub
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, jsonify
from data import Articles
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

pub = RpcPub('db')


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/products')
def products():
    
    #request list of products from Rabit MQ
    
    result = pub.call({'products': 234})
    print(result)
    #if result>0:
    #    return render_template('products.html', articles=articles)
    #else:
    msg = 'Nothing Found'
    return render_template('products.html', msg=result)
    

@app.route('/product/<string:id>')
def product(id):
    
    result = pub.call({'productID':id})
    
    return render_template('product.html', product=product)

#Register from class
class RegisterForm(Form):
    #name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

#REgister user
@app.route('/register', methods=['GET', 'POST'])
def register():
    form= RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        #name = form.name.data
        email= form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        data = jsonify({"email": email, "username": username, "password": password})
                
        pub.call({'register':data})

        
        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html', form=form)

#user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #get fomr fields
        username = request.form['username']
        password_candidate = request.form['password']
        app.logger.info(username)
        #Create cursor
        cur = mysql.connection.cursor()
        #Get user 
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            #get stored hasj
            data = cur.fetchone()
            password = data['password']
            #compare passworda
            if sha256_crypt.verify(password_candidate, password):
                #passes
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)    
            #close connection
            cur.close()    
        else:
            error = 'User not Found'
            return render_template('login.html', error=error)
            
            
    return render_template('login.html')

#Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('you are now logged out', 'success')
    return redirect(url_for('login'))



#Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result>0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    cur.close()

#Article from class

class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = StringField('Body', [validators.Length(min=30)])
    
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title =form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))

        #commit
        mysql.connection.commit()

        cur.close()

        flash('Article create', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)    

@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    #create ciursor
    cur = mysql.connection.cursor()
    #get user
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()
    #get form
    form = ArticleForm(request.form)

    #populate article form fields
    form.title.data = article['title']
    form.body.data = article['body'] 

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        cur = mysql.connection.cursor()

        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s",[title, body, id])

        #commit
        mysql.connection.commit()

        cur.close()

        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)  

#delete article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
