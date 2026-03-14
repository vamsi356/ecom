from flask import Flask, request, render_template, redirect, url_for, session , flash
from otp import genotp
from cmail import send_mail
from stoken import entoken,dctoken
from flask_session import Session
import bcrypt
import mysql.connector
from mysql.connector import (connection)
import os
import uuid
import razorpay
import codecs
import re
import ast
import pdfkit
from razorpay import Client
def uuid_to_bin(uuid_str):
    return uuid.UUID(uuid_str).bytes

def bin_to_uuid(bin_uuid):
    return str(uuid.UUID(bytes=bin_uuid))
client = razorpay.Client(auth=("rzp_test_F5ANeNJTZrJrQS", "1P26IySUPKgpwcx3J8sFf81Y"))
mydb=mysql.connector.connect(user='root',host='localhost',password='Vamsi@383',db='ecom')
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
app.secret_key='codegnan@123'
@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/index')
def index():
    if session.get('user') and not session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
                FROM items
            ''')
            items = cursor.fetchall()
            return render_template('index.html', items=items)
        except Exception as e:
            print(f'Error: {e}')
            flash('Could not load items')
            return redirect(url_for('index'))  # Or another fallback like 'home'
    elif session.get('admin'):
        flash('You are logged in as an admin')
        return redirect(url_for('adminpanel'))
    else:
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
                FROM items
            ''')
            items = cursor.fetchall()
            return render_template('index.html', items=items)
        except Exception as e:
            print(f'Error: {e}')
        return render_template('index.html', items=items)
@app.route('/contact', methods=['GET', 'POST'])
def contact():
     if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['description']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('INSERT INTO contact_submissions (name, email, message) VALUES (%s, %s, %s)', (name, email, message))
            mydb.commit()
            flash('Message sent successfully we will contact you soon')
            return redirect(url_for('contact'))
        except Exception as e:
            print(f"Error in contact form submission: {e}")
            flash('Could not send message')
        return redirect(url_for('contact'))
     return render_template('contact.html')
   
@app.route('/admincreate', methods=['GET', 'POST'])
def admincreate():
    if request.method == 'POST':
        username = request.form['username']
        useremail = request.form['email']
        password = request.form['password']
        address = request.form['address']
        agreed = request.form['agree']
        otp = genotp()
        admindata = {
            'username': username,
            'email': useremail,
            'password': password,
            'address': address,
            'agreed': agreed,
            'otp': otp
        }
        subject = 'OTP for Admin Account Creation'
        body = f'Your OTP is {otp}. Please use this to complete your registration.'
        send_mail(to=useremail, body=body, subject=subject)
        flash(f'OTP sent to {useremail}. Please check your email to complete registration')
        return redirect(url_for('otpverify',endata=entoken(data=admindata)))
    return render_template('admincreate.html')
@app.route('/otpverify/<endata>',methods=['GET', 'POST'])
def otpverify(endata):
    try:
        ddata = dctoken(data=endata)
    except Exception as e:
        print(f"Error in dcode admindata {e}")
        flash('could not verify otp')
        return redirect(url_for('admincreate'))
    else:
        if request.method == 'POST':
            uotp = request.form['otp']
            if uotp == ddata['otp']:
                salt = bcrypt.gensalt()
                hash = bcrypt.hashpw(ddata['password'].encode('utf-8'), salt)
                try:
                    cursor = mydb.cursor(buffered=True)
                    cursor.execute('insert into admindata(username, adminemail, password, address, agree) values(%s,%s,%s,%s,%s)',
                        [ddata['username'], ddata['email'], hash, ddata['address'], ddata['agreed']])
                    mydb.commit()
                except Exception as e:
                    print(f"Error is {e}")
                    flash('could not store data')
                    return redirect(url_for('admincreate'))
                else:
                    flash(f"{ddata['email']} successfully registered")
                    return redirect(url_for('adminlogin'))
            else:
                flash('otp wrong')
                return redirect(url_for('otpverify', endata=endata))
        return render_template('adminotp.html', endata=endata)
@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if not session.get('admin'):
        if request.method == 'POST':
            useremail = request.form['email']
            password = request.form['password'].encode('utf-8')
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('SELECT COUNT(*) FROM admindata WHERE adminemail = %s', [useremail])
                email_count = cursor.fetchone()
                if email_count[0] == 1:
                    cursor.execute('SELECT password FROM admindata WHERE adminemail = %s', [useremail])
                    stored_password = cursor.fetchone()
                    if bcrypt.checkpw(password, stored_password[0]):
                        session['admin'] = useremail
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Password wrong')
                        return redirect(url_for('adminlogin'))
                else:
                    flash('Email not found')
                    return redirect(url_for('adminlogin'))
            except Exception as e:
                print(f"ERROR in login validation: {e}")
                flash('Login failed')
                return redirect(url_for('adminlogin'))

        return render_template('adminlogin.html')
    else:
        flash('You are already logged in')
        return redirect(url_for('adminpanel'))
@app.route('/adminpanel')
def adminpanel():
    if session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('SELECT COUNT(*) FROM items WHERE added_by = %s', [session.get('admin')])
            items_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM orders')
            orders_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM users')
            users_count = cursor.fetchone()[0]
            cursor.execute('select sum(total_amount) from orders')
            total_sales = cursor.fetchone()[0]
            return render_template('adminpanel.html', items_count=items_count, orders_count=orders_count, users_count=users_count, total_sales=total_sales)     
        except Exception as e:
            flash('Could not load admin panel data')
    else:
        return redirect(url_for('adminlogin'))
@app.route('/additem',methods=['GET', 'POST'])
def additem():
    if session.get('admin'):
        if request.method == 'POST':
            itemname = request.form['title']
            itemprice = request.form['price']
            itemdesc = request.form['Discription']
            quantity = request.form['quantity']
            item_category = request.form['category']
            itemimg = request.files['file']
            filename = genotp()+itemimg.filename.split('.')[-1]#generating unique filename
            path = os.path.abspath(__file__)
            print(f"Current file path: {path}")
            dir_path = os.path.dirname(path)
            print(f"Directory path: {dir_path}")
            static_path = os.path.join(dir_path, 'static', 'uploads')
            if not os.path.exists(static_path):
                os.makedirs(static_path)
            print(f"Static uploads path: {static_path}")
            itemimg.save(os.path.join(static_path, filename))
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('INSERT INTO items (itemid, itemname, description, quantity, cost, category, imagename, added_by) VALUES (uuid_to_bin(uuid()), %s, %s, %s, %s, %s, %s, %s)',
                               (itemname, itemdesc, quantity, itemprice, item_category, filename, session['admin']))
                mydb.commit()
                flash('Item added successfully')
            except Exception as e:
                print(f"Error adding item: {e}")
                flash('Failed to add item')
            return redirect(url_for('additem'))
        return render_template('additem.html')
    else:
        return redirect(url_for('adminlogin'))
@app.route('/viewallitems')
def viewallitems():
    if session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
                FROM items 
                WHERE added_by = %s
            ''', [session.get('admin')])
            
            itemsdata = cursor.fetchall()
            return render_template('viewall_items.html', itemsdata=itemsdata)
        
        except Exception as e:
            print(f'Error: {e}')
            flash('Could not fetch items data')
            return redirect(url_for('adminpanel'))
    else:
        flash('Please login first')
        return redirect(url_for('adminlogin'))
@app.route('/view_item/<itemid>')
def view_item(itemid):
    if session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
                FROM items 
                WHERE added_by = %s AND itemid = uuid_to_bin(%s)
            ''', [session.get('admin'), itemid])
            itemdata = cursor.fetchone()
            return render_template('view_item.html', itemdata=itemdata)
        except Exception as e:
            print(f'Error: {e}')
            flash('Could not fetch item data')
            return redirect(url_for('adminpanel'))
    else:
        flash('Please login first')
        return redirect(url_for('adminlogin'))
@app.route('/update_item/<itemid>',methods=['GET','POST'])  
def update_item(itemid):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(itemid),itemname,description,quantity,cost,category,imagename from items where itemid=uuid_to_bin(%s) and added_by=%s',[itemid,session.get('admin')])
            itemdata=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('could not fetch data')   
            return redirect(url_for('viewallitems'))  
        else: 
            if request.method=='POST':
                item_name=request.form['title']
                description=request.form['Description']
                price=request.form['price']
                quantity=request.form['quantity']
                item_category=request.form['category']
                imgdata=request.files['file']
                if imgdata.filename=='':
                    filename=itemdata[6]
                else:
                    filename=genotp()+'.'+imgdata.filename.split('.')[-1]
                    print(filename)
                    path=os.path.abspath(__file__) #finding actual path of app file
                    print(path)
                    dirpath=os.path.dirname(path) #finding directory path of app file
                    print(dirpath)
                    static_path=os.path.join(dirpath,'static') #finding static path of app file
                    print(static_path)
                    os.remove(os.path.join(static_path,itemdata[6]))
                    imgdata.save(os.path.join(static_path,filename))
                cursor.execute('update items set itemname=%s,description=%s,quantity=%s,cost=%s,category=%s,imagename=%s where itemid=uuid_to_bin(%s) and added_by=%s',[item_name,description,quantity,price,item_category,filename,itemid,session.get('admin')])
                mydb.commit()
                flash(f'{item_name} updated successfully')
                return redirect(url_for('view_item',itemid=itemid))
            return render_template('update_item.html',item_data=itemdata)
    else:
        flash('pls login first')
        return redirect(url_for('adminlogin'))  
@app.route('/delete_item/<itemid>', methods=['POST', 'GET'])
def delete_item(itemid):
    if session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                DELETE FROM items 
                WHERE added_by = %s AND itemid = uuid_to_bin(%s)
            ''', [session.get('admin'), itemid])
            mydb.commit()
            flash('Item deleted successfully')
            return redirect(url_for('viewallitems'))
        except Exception as e:
            print(f'Error: {e}')
            flash('Could not delete item')
            return redirect(url_for('viewallitems'))
    else:
        flash('Please login first')
        return redirect(url_for('adminlogin'))
@app.route('/adminupdate', methods=['GET', 'POST'])
def adminupdate():
    if session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('SELECT username,address,fullname,adminemail,role,profile_pic,agree FROM admindata WHERE adminemail = %s', [session.get('admin')])
            admin_data = cursor.fetchone()
            if request.method == 'POST':
                username = request.form['username']
                fullname = request.form['fullname']
                adminmail = request.form['adminemail']
                address = request.form['address']
                role = request.form['role']
                profile_pic = request.files['profile_pic']
                agree = request.form.get('agree')
                cursor = mydb.cursor(buffered=True)
                cursor.execute('UPDATE admindata SET username = %s,fullname = %s,adminemail = %s,address = %s,role = %s,profile_pic = %s WHERE adminemail = %s and agree = %s',
                               (username, fullname, adminmail, address, role,profile_pic, session.get('admin'), agree))
                mydb.commit()
                cursor.close()
                flash('Profile updated successfully')
                return redirect(url_for('adminupdate'))
            return render_template('adminupdate.html', admin_data=admin_data)
        except Exception as e:
            print(f"Error fetching admin data: {e}")
            flash('Could not fetch admin data')
            return redirect(url_for('adminupdate'))
    else:
        flash('Please login first')
        return redirect(url_for('adminlogin'))
@app.route('/usercreate', methods=['GET', 'POST'])
def usercreate():
    if request.method == 'POST':
        username = request.form['username']
        useremail = request.form['email']
        password = request.form['password']
        address = request.form['address']
        gender = request.form['usergender']
        otp = genotp()
        # Hash the password before storing
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
         # Convert bytes to string for storage
        userdata = {
            'username': username,
            'email': useremail,
            'password': hashed_password.decode('utf-8'),
            'address': address,
            'gender': gender,
            'otp': otp
        }
        subject = 'OTP for User Account Creation'
        body = f'Your OTP is {otp}. Please use this to complete your registration.'
        send_mail(to=useremail, body=body, subject=subject)
        flash(f'OTP sent to {useremail}. Please check your email to complete registration')
        return redirect(url_for('userotpverify', endata=entoken(data=userdata)))
    return render_template('usersignup.html')
@app.route('/userotpverify/<endata>', methods=['GET', 'POST'])
def userotpverify(endata):
    if request.method == 'POST':
        otp = request.form['otp']
        userdata = dctoken(endata)
        if otp == userdata['otp']:
            # Create user in the database
            cursor = mydb.cursor(buffered=True)
            try:
                cursor.execute('INSERT INTO users (name, email, address,password, gender) VALUES (%s, %s, %s, %s, %s)',
                               (userdata['username'], userdata['email'], userdata['address'], userdata['password'], userdata['gender']))
                mydb.commit()
            except Exception as e:
                print(f"Error creating user: {e}")
                flash('Could not create user')
                return redirect(url_for('usercreate'))
            flash('User created successfully')
            return redirect(url_for('userlogin'))
        else:
            flash('Invalid OTP')
            return redirect(url_for('userotpverify', endata=endata))
    return render_template('userotp.html')
@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    if not session.get('user'):
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            cursor = mydb.cursor(buffered=True)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode('utf-8'), user[4].encode('utf-8')):
                session['user'] = user[2]
                flash('Login successful')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password')
        return render_template('userlogin.html')
    else:
        flash('You are already logged in')
        return redirect(url_for('index'))
@app.route('/addtocart/<itemid>', methods=['POST', 'GET'])
def addtocart(itemid):
    if session.get('user'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT itemid, itemname, cost 
                FROM items 
                WHERE itemid = uuid_to_bin(%s)
            ''', [itemid])
            product = cursor.fetchone()

            if product:
                cursor.execute('''
                    INSERT INTO cart (user_id, product_id) 
                    VALUES (%s, uuid_to_bin(%s))
                ''', [session['user'], itemid])
                mydb.commit()
                flash('Product added to cart')
            else:
                flash('Product not found')
        except Exception as e:
            print(f'Error: {e}')
            flash('Could not add product to cart')
    else:
        flash('Please login first')
        return redirect(url_for('userlogin'))

    return redirect(url_for('index'))

# @app.route('/addtocart/<itemid>', methods=['POST', 'GET'])
# def addtocart(itemid):  
#     print(f'Item ID in addtocart function: {itemid}')
#     if session.get('user'):  
#         cursor = mydb.cursor(buffered=True)
#         cursor.execute('SELECT * FROM items WHERE HEX(itemid) = %s', (itemid,))
#         product = cursor.fetchone()
#         print(itemid)
#         print(product)
#         print(f"Product fetched: {product}")
#         if product:
#             cursor.execute('INSERT INTO cart (user_id, product_id) VALUES (%s, %s)',
#                            (session['user'], itemid))
#             mydb.commit()
#             flash('Product added to cart')
#         else:
#             flash('Product not found')
#     else:
#         flash('You are not logged in')
#     return redirect(url_for('index'))
@app.route('/category/<category>')
def category(category):
    cursor = mydb.cursor(buffered=True)
    cursor.execute('''
        SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
        FROM items 
        WHERE category = %s
    ''', (category,))
    items = cursor.fetchall()
    cursor.close()

    return render_template('index.html', items=items, category=category)
@app.route('/description/<itemid>')
def description(itemid):
    itemid = uuid.UUID(itemid).bytes  # Convert itemid to bytes
    print(f'Item ID in description function: {itemid}')
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute('''
            SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
            FROM items 
            WHERE bin_to_uuid(itemid) = %s
        ''', [bin_to_uuid(itemid)])  
        item = cursor.fetchone()
        cursor.close()
        print(f'Item fetched: {item}')
        return render_template('description.html', item=item)

    except Exception as e:
        print(e)
        flash("Could not fetch item description")
        return redirect(url_for('index'))
@app.route('/cart')
def cart(): 
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('''
        SELECT 
            p.itemid, 
            p.itemname, 
            p.description, 
            p.cost, 
            p.category, 
            p.imagename,
            p.quantity 
        FROM cart c 
        JOIN items p ON c.product_id = p.itemid 
        WHERE c.user_id = %s
    ''', (session['user'],))

        items = cursor.fetchall()
        return render_template('cart.html', items=items)
    else:
        flash('Please Login to view cart')
        return redirect(url_for('userlogin'))
@app.route('/removecart/<itemid>')
def removefromcart(itemid):
    if session.get('user'):
        try:
            itemid_bytes = uuid.UUID(itemid).bytes
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'DELETE FROM cart WHERE user_id = %s AND product_id = %s',
                (session['user'], itemid_bytes)
            )
            mydb.commit()
            cursor.close()

            if cursor.rowcount == 0:
                flash('Item not found in cart')
            else:
                flash('Item removed from cart')
        except ValueError:
            flash(f'Invalid item ID format: {itemid}')
        except Exception as e:
            print(e)
            flash('Could not remove item')
        return redirect(url_for('cart'))
    else:
        flash('Please login first')
        return redirect(url_for('userlogin'))
@app.route('/pay/<itemid>/<dqyt>/<float:price>', methods=['GET', 'POST'])
def pay(itemid, dqyt, price):
    if session.get('user'):
        itemid = uuid.UUID(itemid).bytes
        print(f'Item ID in pay function: {itemid}')
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename 
                FROM items 
                WHERE bin_to_uuid(itemid) = %s
            ''', [bin_to_uuid(itemid)])
            item = cursor.fetchone()
            cursor.close()
            print(f'Item fetched: {item}')
            print(f'Item ID: {itemid}, Quantity: {dqyt}')
            print(bin_to_uuid(itemid))
        except Exception as e:
            print(e)
            flash('Could not fetch details')
            return redirect(url_for('index'))

        try:
            if request.method == 'POST':
                qyt = int(request.form['qyt'])
            else:
                qyt = int(dqyt)

            price = price * 100  # Convert to paise
            amount = price * qyt
            print(amount, qyt, price)
            print(f'Creating payment for item {item[1]}, with {amount}')
            order = client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture": "1"
            })
            itemid = itemid.hex()  # Gives you '4f0c68566df0b8b925caee48xxxxxxxx'
            print(f'Order created: {order} and item ID: {itemid}')
            return render_template('pay.html', qyt=qyt, order=order, amount=amount, itemid=itemid, name=item[1])

        except Exception as e:
                print(f'Could not place order: {e}')
                return redirect(url_for('index'))

    else:  
        flash('pls login first')
        return redirect(url_for('userlogin'))
@app.route('/success', methods=['GET', 'POST'])
def success():
    if request.method == 'POST':
        # ... (all request.form lines are the same)
        payment_id = request.form["razorpay_payment_id"]
        order_id = request.form["razorpay_order_id"]
        order_signature = request.form["razorpay_signature"]
        item_id = request.form["itemid"]
        name = request.form["name"]
        item_qyt = request.form["quantity"]
        total_amount = request.form["total_amount"]
        
  
        params_dict = {
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': order_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return 'Payment verification failed', 400
        else:
            cursor = mydb.cursor(buffered=True)

            # --- START OF FIX ---
            # Fetch item details by passing the item_id string directly.
            # The database will handle the conversion with `bin_to_uuid(itemid)`
            
            # OLD LINE (causes ValueError):
            # cursor.execute('...WHERE bin_to_uuid(itemid) = %s', (bin_to_uuid(item_id),))

            # NEW CORRECTED LINE:
            cursor.execute('SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename FROM items WHERE itemid = UNHEX(%s)', (item_id,))
            # --- END OF FIX ---
            
            item = cursor.fetchone()
            print(f'Item fetched for order: {item}')
            print(f'Item ID: {item_id}, Quantity: {item_qyt}, Total Amount: {total_amount}')

            # The rest of your code with the previous check remains the same
            if item:
                # Get user data
                user_email = session.get('user')
                if not user_email:
                    flash('User session not found. Please log in again.')
                    cursor.close()
                    return 'redirect_to_login'

                cursor.execute('SELECT * FROM users WHERE email = %s', (user_email,))
                userdata = cursor.fetchone()

                if not userdata:
                    flash('User not found in database.')
                    cursor.close()
                    return 'user_not_found_error'

                # Update quantity
                # NOTE: You will need to use item_id for the WHERE clause here, not the binary version.
                new_quantity = item[3] - int(item_qyt)
                cursor.execute('UPDATE items SET quantity = %s WHERE itemid = UNHEX(%s)', (new_quantity, item_id))


                # Insert into orders
                cursor.execute('INSERT INTO orders(item_name, total_amount, quantity, payment_by, address) VALUES (%s, %s, %s, %s, %s)',
                               (name, total_amount, item_qyt, user_email, userdata[3]))  # Assuming address is at index 3

                mydb.commit()
                cursor.close()

                flash('Order placed successfully')
                return render_template('success.html')
            else:
                # Handle the case where the item_id is not found
                cursor.close()
                flash('Error: Item not found in the database.')
                return 'item_not_found_error', 404
@app.route('/myorders', methods=['GET', 'POST'])
def myorders():
    if session.get('user'):
        user_email = session.get('user')
        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT * FROM orders WHERE payment_by = %s', (user_email,))
        orders = cursor.fetchall()
        cursor.close()
        if not orders:
            flash('No orders found for this user')
            return render_template('orders.html', user_orders=[])
        return render_template('orders.html', user_orders=orders)
    else:
        flash('Please log in to view your orders', 'warning')
        return redirect(url_for('userlogin'))
@app.route('/viewallorders')
def viewallorders():
    if session.get('admin'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''
                SELECT o.order_id, o.item_name, o.total_amount, o.quantity, o.payment_by, o.address, u.name 
                FROM orders o 
                JOIN users u ON o.payment_by = u.email
            ''')
            orders = cursor.fetchall()
            cursor.execute('select date_format(order_date, "%D %M %Y") from orders')
            order_dates = cursor.fetchall()
            cursor.close()
            return render_template('viewallorders.html', orders=orders, order_dates=order_dates)
        except Exception as e:
            print(f'Error: {e}')
            flash('Could not fetch orders')
            return redirect(url_for('adminpanel'))
@app.route('/addreview/<itemid>', methods=['GET', 'POST'])
def addreview(itemid):
    if session.get('user'):
        print(f'Item ID in addreview function: {itemid}')
        print(uuid.UUID(itemid).bytes)
        print(f'User ID: {session.get("user")}')
        if request.method == 'POST':
            review = request.form['review']
            rating = request.form['rate']
            
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'INSERT INTO reviews (review, rating, itemid, user) VALUES (%s, %s, %s, %s)',
                [review, rating, uuid.UUID(itemid).bytes, session.get('user')]
            )
            mydb.commit()
            cursor.close()
            
            flash('Review added successfully', 'success')
            return redirect(url_for('description',itemid=itemid))
        
        return render_template('review.html')
    else:
        flash('Please log in to add a review', 'warning')
        return redirect(url_for('userlogin'))
@app.route('/readreview/<itemid>')
def readreview(itemid):
    cursor = mydb.cursor(buffered=True)
    cursor.execute(
        'SELECT review, rating, user FROM reviews WHERE itemid = UUID_TO_BIN(%s)',
        [itemid]
    )
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('readreview.html', item_data=reviews)
@app.route('/searchdata', methods=['POST'])
def searchdata():
    if request.method == 'POST':
        sdata = request.form['search']
        strg = 'A-Za-z0-9'
        MATCHING_STRG = re.compile(f'^[{strg}]', re.IGNORECASE)
        if MATCHING_STRG.search(sdata):
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('''
                    SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename
                    FROM items
                    WHERE itemname LIKE %s
                    OR description LIKE %s
                    OR category LIKE %s
                    OR CAST(cost AS CHAR) LIKE %s
                ''', ['%' + sdata + '%', '%' + sdata + '%', '%' + sdata + '%', '%' + sdata + '%'])

                results = cursor.fetchall()
                print(results)
                cursor.close()

                items = []
                for row in results:
                    items.append(list(row))  # No conversion of UUID

                if items:
                    return render_template('dashboard.html', items=items)
                else:
                    flash("Nothing found")
                    return render_template('index.html')

            except Exception as e:
                print(e)
                flash('Could not fetch search items')
                return redirect(url_for('index'))
        else:
            flash('Invalid search data, please enter some value')
            return redirect(url_for('index'))
@app.route('/search_order_id', methods=['GET'])
def search_order_id():
    if request.method == 'GET':
        order_id = request.args.get('search')
        if order_id:
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('''
                    SELECT o.order_id, o.item_name, o.total_amount, o.quantity, o.payment_by, o.address, u.name 
                    FROM orders o 
                    JOIN users u ON o.payment_by = u.email
                    WHERE o.order_id = %s
                ''', (order_id,))
                order = cursor.fetchone()
                cursor.close()

                if order:
                    return render_template('view_order.html', order=order)
                else:
                    flash('Order not found')
                    return redirect(url_for('viewallorders'))
            except Exception as e:
                print(f'Error: {e}')
                flash('Could not fetch order details')
                return redirect(url_for('viewallorders'))
        else:
            flash('Please provide an order ID')
            return redirect(url_for('viewallorders'))
# @app.route('/searchdata', methods=['GET', 'POST'])
# def searchdata():
#     if request.method == 'POST':
#         sdata = request.form['search']
#         strg = 'A-Za-z0-9'
#         MATCHING_STRG = re.compile(f'^[{strg}]', re.IGNORECASE)
#         if MATCHING_STRG.search(sdata):
#             try:
#                 cursor = mydb.cursor(buffered=True)
#                 cursor.execute('''
#                     SELECT bin_to_uuid(itemid), itemname, description, quantity, cost, category, imagename
#                     FROM items
#                     WHERE itemname LIKE %s
#                     OR description LIKE %s
#                     OR category LIKE %s
#                     OR CAST(cost AS CHAR) LIKE %s
#                 ''', ['%' + sdata + '%', '%' + sdata + '%', '%' + sdata + '%', '%' + sdata + '%'])

#                 results = cursor.fetchall()
#                 print(results)
#                 cursor.close()
#                 import uuid

#                 items = []
#                 for row in results:
#                     items.append(list(row))  # No conversion of UUID


#                 # Convert UUID string to UUID object for .hex() to work in Jinja
                
#                 if items:
#                     return render_template('dashboard.html', items=items)
#                 else:
#                     flash("Nothing found")
#                     return render_template('index.html')

#             except Exception as e:
#                 print(e)
#                 flash('Could not fetch search items')
#                 return redirect(url_for('index'))
#         else:
#             flash('invalid search data pls enter some value')
#             return redirect(url_for('index'))
@app.route('/logout')
def logout():
    if session.get('admin'):
        session.pop('admin', None)
        flash('Admin logged out successfully')
        return redirect(url_for('index'))
    elif session.get('user'):
        session.pop('user', None)
        flash('User logged out successfully')
        return redirect(url_for('index'))
    else:
        flash('You are not logged in')
        return redirect(url_for('index'))
app.run(debug=True)