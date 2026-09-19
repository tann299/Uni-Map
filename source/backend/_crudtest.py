import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
from django.conf import settings
settings.DATABASES['default'] = {'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}
settings.ALLOWED_HOSTS += ['testserver']
django.setup()
from django.test.utils import setup_test_environment
setup_test_environment()
from django.db import connection
from django.core.management import call_command
call_command('migrate', run_syncdb=True, verbosity=0)
with connection.cursor() as c:
    c.execute('CREATE TABLE mon(ma_mon varchar(15) primary TNT API, ten_mon varchar(60), la_nang_khieu bool, thu_tu int)')
    c.execute('CREATE TABLE ho_so_nang_luc(id integer primary TNT API autoincrement, user_id int, ten_ho_so varchar(100), phuong_thuc varchar(13), diem_uu_tien decimal, vung_mien_uu_tien varchar(60), ngay_tao datetime, ngay_sua datetime)')
    c.execute('CREATE TABLE diem_mon(ho_so_id int, ma_mon varchar(15), diem decimal, primary TNT API(ho_so_id,ma_mon))')
    c.execute('CREATE TABLE nhom_nganh_quan_tam(ho_so_id int, nhom_nganh varchar(40), primary TNT API(ho_so_id,nhom_nganh))')
    c.execute('CREATE TABLE to_hop(ma_to_hop varchar(5) primary TNT API, ten_to_hop varchar(80), cac_mon varchar(60), so_mon int, nguon varchar(20))')
    for m,tn,nk,tt in [('TOAN','Toan',0,1),('LI','Vat ly',0,4),('HOA','Hoa hoc',0,5),('ANH','Tieng Anh',0,3)]:
        c.execute('INSERT INTO mon(ma_mon,ten_mon,la_nang_khieu,thu_tu) VALUES(?,?,?,?)',(m,tn,nk,tt))
    for m,cm,s in [('A00','TOAN,LI,HOA',3),('A01','TOAN,LI,ANH',3)]:
        c.execute('INSERT INTO to_hop(ma_to_hop,ten_to_hop,cac_mon,so_mon,nguon) VALUES(?,?,?,?,?)',(m,m,cm,s,'test'))

from django.contrib.auth.models import User
from django.test import Client
u = User.objects.create_user('hs1','','Matkhau123!')
c = Client(); c.force_login(u)
print('GET danh sach:', c.get('/ho-so/').status_code, '| GET tao:', c.get('/ho-so/tao/').status_code)
data = {'ten_ho_so':'Thi thu lan 1','phuong_thuc':'Diem thi THPT','diem_uu_tien':'0','vung_mien_uu_tien':'',
  'diemmon_set-TOTAL_FORMS':'6','diemmon_set-INITIAL_FORMS':'0','diemmon_set-MIN_NUM_FORMS':'0','diemmon_set-MAX_NUM_FORMS':'1000'}
for i,(m,d) in enumerate([('TOAN','8.5'),('LI','7.75'),('HOA','8.0'),('ANH','9.0')]):
    data[f'diemmon_set-{i}-ma_mon']=m; data[f'diemmon_set-{i}-diem']=d
r = c.post('/ho-so/tao/', data); print('POST tao:', r.status_code, getattr(r,'url',''))
from tracuu.models import HoSoNangLuc, DiemMon
hs = HoSoNangLuc.objects.get(user=u)
print('  ho so id', hs.pk, '| so mon', DiemMon.objects.filter(ho_so=hs).count())
r = c.get(f'/ho-so/chi-tiet/{hs.pk}/'); h=r.content.decode()
print('GET chi tiet:', r.status_code, '| A00', 'A00' in h, '| 24.25', '24.25' in h, '| 25.25', '25.25' in h)
data2 = dict(data); data2['ten_ho_so']='Da sua'; data2['diemmon_set-INITIAL_FORMS']='4'
for i,(m,d) in enumerate([('TOAN','8.5'),('LI','7.75'),('HOA','8.0'),('ANH','9.0')]):
    data2[f'diemmon_set-{i}-ho_so']=str(hs.pk)
r=c.post(f'/ho-so/sua/{hs.pk}/',data2); print('POST sua:', r.status_code, getattr(r,'url',''), '| ten moi', HoSoNangLuc.objects.get(pk=hs.pk).ten_ho_so)
u2=User.objects.create_user('hs2','','Matkhau123!'); c2=Client(); c2.force_login(u2)
print('user khac GET chi tiet:', c2.get(f'/ho-so/chi-tiet/{hs.pk}/').status_code, '(404)')
print('GET xoa:', c.get(f'/ho-so/xoa/{hs.pk}/').status_code, '| POST xoa:', c.post(f'/ho-so/xoa/{hs.pk}/').status_code, getattr(c.post(f'/ho-so/xoa/{hs.pk}/'),'url',''), '| con lai', HoSoNangLuc.objects.filter(user=u).count())
c3=Client(); print('chua login GET:', c3.get('/ho-so/').status_code, '(302)')
