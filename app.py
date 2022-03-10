from flask import Flask, render_template, request, url_for, session,send_from_directory
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from mailmerge import MailMerge
import secrets
import textract
from cryptography.fernet import Fernet
from datetime import date
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
mail= Mail(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'nchizampeni@gmail.com'
app.config['MAIL_PASSWORD'] = 'Chiz@mpeni95'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
app.config['SECRET_KEY'] = "a_secret_key_should_be_added_here"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.db"
db = SQLAlchemy(app)
#-----------------------------------------------------------------------
def encrypt_document(path):
        text = textract.process(path)
        text = text.decode('utf-8')
        text = text.replace(' ','')
        text = text.replace('\n','')
        key = Fernet.generate_key()
        fernet = Fernet(key)
        #encrypt and decrypt string
        hash = fernet.encrypt(text.encode())
        return text
#-----------------------------------------------------------------------

class Users(db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    email  = db.Column(db.String(50))
    name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    password  = db.Column(db.String(50))
    userType = db.Column(db.String(50))
    initial = db.Column(db.String(5))


class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hash  = db.Column(db.String(200), default='None')
    key  = db.Column(db.String(200), default='None')
    issuer = db.Column(db.String(200), default='None')
    awarded_to = db.Column(db.String(200), default='None')
    expiry = db.Column(db.String(200), default=date.today())
    status = db.Column(db.String(200), default='active')
    
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(50))
    template = db.Column(db.String(500), default='template1')
    validation_period = db.Column(db.Integer)
    issuer = db.Column(db.String(50))


 #-----------------------------------------------------------------------
def auth(email, password):
    user =Users.query.filter_by(email=email, password=password).first()
    if user != None:
        return user         
    return None
#-----------------------------------------------------------------------
@app.route('/', methods = ['POST','GET'])
def index():
    error = 0
    session['user'] = None 
    sett = Settings.query.first()
    session['settings'] ={'email':sett.email, 'template':sett.template,'validation':sett.validation_period,'issuer':sett.issuer}
    print('TEMPLATE:',session['settings'])
    if request.method == 'POST':
        user = auth(request.form['email'], request.form['password'])
        if user != None:
            session['user'] = {'id':user.id,'name':user.surname, 'initial':user.initial, 'type':user.userType}
            return dashboard()
    template = 'account/auth-normal-sign-in.html'
    return render_template(template,error=error)
#-----------------------------------------------------------------------
@app.route('/dashboard')
def dashboard():
    sett = Settings.query.first()
    session['settings'] ={'email':sett.email, 'template':sett.template,'validation':sett.validation_period,'issuer':sett.issuer}
    total_cert = len(Certificate.query.all())
    active = len(Certificate.query.filter_by(status='active').all())
    expired = total_cert - active
    users = len(Users.query.all())
    template = 'dashboard/index.html'
    ob =Certificate.query.all()
    return render_template(template,total=total_cert,users=users,active=active,expired=expired,error=99,cert=ob, user = session['user'])

@app.route('/verifyCertificate', methods=['POST','GET'])
def verifyCertificate():
    status = False
    report = False
    issuer  = None
    expiry = None
    if request.files:
        file = request.files['file']
        file.save(os.path.join("static/certificates/temp", file.filename))
        data = encrypt_document(os.path.join("static/certificates/temp", file.filename))
        cert = Certificate.query.filter_by(key = data[:48], hash=data).first()
    
        if cert != None:
            status = True
            expiry = cert.expiry
            issuer = cert.issuer
        report =True
    template = 'dashboard/verifyCertificate.html'
    return render_template(template,status=status, report =report,issuer = session['settings'].get('issuer'), date = expiry, user = session['user'])

@app.route('/certificates/<opt>', methods=['POST','GET'])
def certificates(opt):
    status=0
    if request.method == 'POST':
        data = request.form.to_dict()
        document = MailMerge('static/certificates/template/'+str(session['settings'].get('template'))+'.docx')
        key = secrets.token_hex(24)
        document.merge(
            serviceNumber = data.get('providerNumber'),
            name = data.get('recipient'),
           position = data.get('operator'),
            key = key,
            date = str(date.today()),
            issuer = session['settings'].get('issuer')
        )
        doc_path = 'static/certificates/'+str(data.get('recipient'))+str('.docx')
        try:
            document.write(doc_path)
            cert = Certificate(key= encrypt_document(doc_path)[:48], hash=encrypt_document(doc_path),expiry=data.get('expiry'),awarded_to=data.get('recipient'), issuer = session['settings'].get('issuer') )
            db.session.add(cert)
            status = 'Certificate for '+data.get('recipient')+' has been created successfully'
            db.session.commit()
        except Exception as e:
            print(e)
            status = 'Certificate for '+data.get('recipient')+' could not be created'
    template = 'dashboard/newCertificate.html'
    return render_template(template,error=99,opt=opt,status=status, user = session['user'])


@app.route('/mailCertificate', methods = ['POST','GET'])
def mailCertificate():
    status = 0
    if request.method == 'POST':
        data = request.form.to_dict()
        msg = Message('Hello', sender = session.get('email'), recipients = data.get('recipient'))
        msg.body = "Hello Flask message sent from Flask-Mail"
        with app.open_resource('static/certificates/'+data.get('cert')) as certificate:
                msg.attach(data.get('cert'),'application/vnd.openxmlformats-officedocument.wordprocessingml.document',certificate.read())
        try:
            mail.send(msg)
            status = 'Email successfully sent'
        except Exception as e:
            print(e)
            status= 'Email could not be delivered'
    onlyfiles = [f for f in os.listdir('static/certificates')]
    onlyfiles.remove('template')
    onlyfiles.remove('temp')
    template = 'dashboard/mailCertificate.html'
    return render_template(template,error=99,status=status,cert=onlyfiles, user = session['user'])


@app.route('/logOut')
def logOut():
    template = 'account/auth-normal-sign-in.html'
    return render_template(template)

@app.route("/download/<string:name>")
def download(name):
    download_file = name
    print('downloading ',name)
    try:
        return send_from_directory(directory='static\certificates',filename=download_file) 
    except Exception as e:
        print(e)

@app.route("/test")
def test():
   msg = Message('Hello', sender = 'nchizampeni@gmail.com', recipients = ['nyashac@petalmafrica.com'])
   msg.body = "Hello Flask message sent from Flask-Mail"
   mail.send(msg)
   return "Sent"


@app.route('/settings', methods=['POST','GET'])
def settings():
    sett = Settings.query.first()
    data = {'email':sett.email, 'template':sett.template,'validation':sett.validation_period,'issuer':sett.issuer}
    template = 'dashboard/settings.html'
    if request.method == 'POST':
        data = request.form.to_dict()
        set = Settings.query.first()
        set.validation_period = data.get('validation')
        set.issuer = data.get('issuer')
        set.email = data.get('email')
        set.template = data.get('template')
        db.session.add(set)
        db.session.commit()
    return render_template(template,error=99, user = session['user'], job=data)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')