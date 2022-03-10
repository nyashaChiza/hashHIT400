import textract
from mailmerge import MailMerge

from cryptography.fernet import Fernet
'''
#extract text from document
text = textract.process('Copy.docx')
text = text.decode('utf-8')
text = text.replace(' ','')
text = text.replace('\n','')
#print(text)

key = Fernet.generate_key()
fernet = Fernet(key)
#encrypt and decrypt string
hash = fernet.encrypt(text.encode())
hashed = fernet.decrypt(hash).decode()
print(hashed)
'''
document = MailMerge('Copy.docx')
print(document.get_merge_fields())
data = {'servicenumber':66738, 'recipient':'Tafara Ncube','operator':'Nyasha' }
from datetime import date
document.merge(
            serviceNumber = 66738,
            name = 'Tafara Ncube',
            position = 'Best GF Ever',
            key = 'gff',
            date = str(date.today()),
            issuer = 'Nyasha Chizampeni',
        )
document.write(str(data.get('recipient'))+str('.docx'))

