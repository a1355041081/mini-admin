from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify, after_this_request
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:KELE0514@localhost:3306/miniprogram'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
user_image_collection = db.Table('user_image_collection',
                                 db.Column('user_id', db.String(16), db.ForeignKey('user.id'), primary_key=True),
                                 db.Column('image_id', db.Integer, db.ForeignKey('image.id'), primary_key=True),
                                 )
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(16), primary_key=True)
    name = db.Column(db.String(50))
    openid = db.Column(db.String(128))
    collections = db.relationship('Image', secondary=user_image_collection, backref='users')
    orders = db.relationship('Order', backref='user')
class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    category = db.Column(db.String(16))
    src = db.Column(db.String(200))
    thumb = db.Column(db.String(200))
    is_collected = False # add a new attribute to each image indicating whether it is in the user's collections
class OrderDetail(db.Model):
    __tablename__ = 'order_detail'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text = db.Column(db.String(200))
    image_path = db.Column(db.String(200))
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50))
    status = db.Column(db.String(50))#已下单、已结束
    quantity = db.Column(db.Integer) #新增数量字段
    order_time = db.Column(db.DateTime) #新增下单时间字段
    category = db.Column(db.String(50)) #新增类别字段
    payment_status = db.Column(db.String(50)) #新增付款情况字段
    payment_amount = db.Column(db.Float) #新增付款金额字段
    details = db.relationship('OrderDetail', backref='order') #修改details字段为关联OrderDetail类
    user_id = db.Column(db.String(16), db.ForeignKey('user.id'))

@app.route('/')
def admin():
    return render_template('login.html')

@app.route('/check', methods=['POST'])
def check():
    username = request.form['username']
    password = request.form['password']
    if username == 'admin' and password == '123456':
        return redirect(url_for('main'))
    else:
        return render_template('login.html', error='无效账户名或密码')

@app.route('/main')
def main():
    images = Image.query.all()
    return render_template('main.html',images=images)

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        # Get the uploaded file
        file = request.files['example-image']
        # Generate a unique ID for the file
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        # Save the file to the server
        folder_path = os.path.join(os.getcwd()+'/images')
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file.save(os.path.join(folder_path, filename))
        # Create a new instance of the Image model
        name = request.form['example-name']
        category = request.form['example-category']
        image = Image(name=name, category=category, src='https://www.muke0514.online:5001/images/'+filename, thumb='https://www.muke0514.online:5001/images/'+filename)
        # Add the instance to the database session and commit the changes
        db.session.add(image)
        db.session.commit()
        images =Image.query.all()
        return render_template('main.html', images=images)

@app.route('/images/<filename>')
def get_image(filename):
    folder_path = os.path.join(os.getcwd()+'/images')
    return send_from_directory(folder_path, filename)

@app.route('/delete/image/<imageid>')
def delete_image(imageid):
    image = Image.query.filter_by(id=imageid).first()
    if image:
        # Delete the image file from the server
        os.remove(os.getcwd() + image.src.split('https://www.muke0514.online:5001')[1])
        # Delete the instance from the database session and commit the changes
        db.session.delete(image)
        db.session.commit()
    images = Image.query.all()
    return render_template('main.html', images=images)

@app.route('/delete/order/<orderid>')
def delete_order(orderid):
    order = Order.query.filter_by(id=orderid).first()
    if order:
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for('orders'))

@app.route('/orders')
def orders():
    orders = Order.query.all();
    return render_template('orders.html', orders=orders)

@app.route('/getorder/<orderid>')
def get_order(orderid):
    order = Order.query.filter_by(id=orderid).first()
    return jsonify({'id' : order.id, 'name' : order.name, 'status' : order.status, 'quantity' : order.quantity, 'order_time' : str(order.order_time), 'category' : order.category, 'payment_status' : order.payment_status, 'payment_amount' : order.payment_amount})
@app.route('/updateorder/<order_id>', methods=['POST'])
def update_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return 'Order not found', 404
    order.name = request.form['name']
    order.status = request.form['status']
    order.quantity = request.form['quantity']
    order.order_time = datetime.strptime(request.form['order_time'], '%Y-%m-%d %H:%M:%S')
    order.category = request.form['category']
    order.payment_status = request.form['payment_status']
    order.payment_amount = request.form['payment_amount']

    @after_this_request
    def update_database(response):
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

        return response

    return redirect(url_for('orders'))

@app.route('/orderdetail/<order_id>', methods=['POST'])
def get_order_details(order_id):
    order_details = OrderDetail.query.filter_by(order_id=order_id).all()
    return jsonify([{'text' : order_detail.text, 'image_path' : order_detail.image_path} for order_detail in order_details])

@app.route('/detail/<image_path>')
def get_detail_image(image_path):
    detail_image_path = image_path
    path = detail_image_path.split("-")
    folder_path = os.path.join("C:/Users/Administrator/Desktop/miniprogram-ba/miniprogram/orderdetail/" + path[0])
    return send_from_directory(folder_path, path[1])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context=("9976544_www.muke0514.online.pem","9976544_www.muke0514.online.key"))