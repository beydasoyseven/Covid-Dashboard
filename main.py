from datetime import datetime, timedelta, date
import json
import matplotlib.pyplot as plt
import matplotlib.dates as dates
from matplotlib.dates import drange, MO
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import tkinter as tk
import sqlite3

# https://www.w3resource.com/python-exercises/date-time-exercise/python-date-time-exercise-50.php
def daterange(date1, date2):
    for n in range(int((date2 - date1).days)+1):
        yield date1 + timedelta(n)

def veritabanindan_ulkeleri_getir():
    ulke_liste_sorgusu = 'SELECT Country from Ulkeler'
    veritabani_imleci.execute(ulke_liste_sorgusu)
    ulke_listesi = veritabani_imleci.fetchall()
    return ulke_listesi

#veritabanı olusturdum
veritabani = sqlite3.connect('covid.db')
# SQL sorgulari yapabilmek icin imlec olusturdum
veritabani_imleci = veritabani.cursor()

#ulkeler tablosunu olusturdum
ulke_tablo_sorgusu = 'create table if not exists Ulkeler ( Country TEXT, Slug TEXT, ISO2 TEXT, UNIQUE(Slug))'
#data tablosu olusturdum
data_tablo_sorgusu = 'create table if not exists Veri (Slug TEXT, Date TEXT, Confirmed INT, Deaths INT, Recovered INT, Active INT)'


#eger ulke ve data tablosu olusurken hata gelirse yapılması gerekenleri gosterdim
try:
    veritabani_imleci.execute(ulke_tablo_sorgusu)
    veritabani_imleci.execute(data_tablo_sorgusu)
except sqlite3.Error as sql_hata:
    print("Veritabani hatasi: ", sql_hata)
except Exception as sorgu_hata:
    print("Sorgu hatasi: ", sorgu_hata)


covid_durum_list = ["Confirmed", "Deaths", "Recovered", "Active", "Confirmed-Daily", "Deaths-Daily", "Recovered-Daily", "Active-Daily"]


ulkeler = veritabanindan_ulkeleri_getir()

#eger veritabanından ulkeler gelmezse apiden ulkeleri çekmeyi gösterdim
if len(ulkeler) <= 0:
    ulke_liste_api_url = "https://api.covid19api.com/countries"
    ulkeler_cevap = requests.get(ulke_liste_api_url)
    ulkeler_json = ulkeler_cevap.json()

    for ulke_json in ulkeler_json:
        ulke = ulke_json["Country"]
        slug = ulke_json['Slug']
        iso = ulke_json['ISO2']
        try:
            veritabani_imleci.execute('INSERT OR IGNORE INTO Ulkeler VALUES (?,?,?)', (ulke, slug, iso))
        except sqlite3.Error as sql_hata:
            print("Veritabani hatasi: ", sql_hata)
        except Exception as sorgu_hata:
            print("Sorgu hatasi: ", sorgu_hata)
    veritabani.commit() # Performans icin, insert islemleri bittikten sonra tek bir defada commit islemi uyguluyoruz
    ulkeler = veritabanindan_ulkeleri_getir()

ulkeler.sort()

for i in ulkeler:
    print(i)

def slug_sorgula(ulke): 
    print(ulke)
    ulke_liste_sorgusu = 'SELECT Slug from Ulkeler WHERE Country=?'
    veritabani_imleci.execute(ulke_liste_sorgusu, ulke)
    slug = veritabani_imleci.fetchone()
    return slug

def veri_guncel_mi(ulke_slug):
    guncel_tarih = (datetime.today() - timedelta(days=2)).strftime('%Y-%m-%d')
    return tarih_varsa_atla(ulke_slug, guncel_tarih)

def verileri_cek(secilen_ulke):
    covid_veri_api_url = "https://api.covid19api.com/total/dayone/country/{}".format(secilen_ulke)
    covid_veri_cevap = requests.get(covid_veri_api_url)
    covid_veri_json = covid_veri_cevap.json()
    return covid_veri_json

def tarih_varsa_atla(ulke_slug, tarih):
    print(ulke_slug, tarih)
    tarih_sorgusu = 'SELECT * from Veri WHERE Slug=? AND Date=?'
    # ulke_slug'i veritabanindan cektigimiz icin, sonuc hala tuple icinde, sadece string'i gonderebilmek icin, [0] index'i ile string halini cagirdim
    # ulke_slug = ("germany",)
    # ulke_slug[0] = "germany"
    veritabani_imleci.execute(tarih_sorgusu, (ulke_slug[0], tarih))
    sonuc = veritabani_imleci.fetchone()
    return bool(sonuc)


def verileri_kaydet(ulke_slug, veri):
    # veri = [{"Date": "", "Confirmed": 0, ...}, {"Date": "", "Confirmed": 0, ...}, {"Date": "", "Confirmed": 0, ...}]
    # gunluk_veri = {"Date": "", "Confirmed": 0, ...},
    for gunluk_veri in veri:
        date = gunluk_veri['Date']
        date = date[0: date.index("T")] #saati dahil etmemek için tarihin başlangıc indeksinden saate kadar olan indeksi aldım
        if tarih_varsa_atla(ulke_slug, date):
            continue
        try: # Slug, Date, Confirmed, Deaths, Recovered, Active, ConfirmedDaily, DeathsDaily, RecoveredDaily, ActiveDaily

            confirmed = gunluk_veri['Confirmed']
            deaths = gunluk_veri['Deaths']
            recovered = gunluk_veri['Recovered']
            active = gunluk_veri['Active']
            veritabani_imleci.execute('INSERT INTO Veri VALUES (?,?,?,?,?,?)', (ulke_slug[0], date, confirmed, deaths, recovered, active))
        except sqlite3.Error as sql_hata:
            print("Veritabani hatasi: ", sql_hata)
        except Exception as sorgu_hata:
            print("Sorgu hatasi: ", sorgu_hata)

    veritabani.commit()

ulke_verisi = []

def ulke_liste_secim_dinleyicisi(evt):
    global ulke_verisi
    list_data.selection_clear(0, tk.END)
    frame_baslik.grid_forget()
    frame5.grid_forget()
    frame3.grid(row=0, rowspan=3, column=1, columnspan=5, padx=10, sticky='wesn')
    dinlenen_liste = evt.widget
    index = dinlenen_liste.curselection()
    if len(index) < 1:
        return
    secilen_ulke = dinlenen_liste.get(index)
    ulke_slug = slug_sorgula(secilen_ulke)
    if not veri_guncel_mi(ulke_slug):   #eger guncel degilse iceri girer
        api_cevap = verileri_cek(ulke_slug)
        verileri_kaydet(ulke_slug, api_cevap)
    else:
        print('{} ulkesinin verileri guncel!'.format(ulke_slug[0]))
    veritabani_imleci.execute('SELECT * from Veri WHERE Slug=?', ulke_slug)
    sonuc = veritabani_imleci.fetchall()



    label3 = tk.Label(
        frame3,
        text="Verileriniz çekildi görüntülemek için lütfen bir filtre seçiniz !",
        font="Calibri 20",
        background="dodger blue",
        fg="white",
        anchor="n",
        width=58,
        height=1,
        border=3,
        relief="raised")
    label3.grid(row=0, column=0)
    ulke_verisi = sonuc
    print(sonuc)

def data_filtre_secim_dinleyicisi(evt):
    global ulke_verisi
    frame3.grid_forget()
    frame_baslik.grid_forget()
    frame5.grid(row=0, rowspan=2, column=3, columnspan=5)
    dinlenen_liste = evt.widget
    index = dinlenen_liste.curselection()
    secilen_filtre = index[0]
    if len(index) < 1 or len(ulke_verisi) < 1:
        return
    # buradaki kod guncelleme sorununu cozdu: https://www.it-swarm.dev/tr/python/matplotlibdeki-arsa-dinamik-olarak-guncelleniyor/1066582657/
    veri_x = []
    veri_y = []

    onceki_gun_verisi = None
    for veri in ulke_verisi:
        veri_x.append(veri[1])
        secim_indexi = (secilen_filtre % 4) + 2 #arayüzden confirmed seçersek index[0]=0 gelir.veri[0+2]=2 olur bu da konsoldaki 3.elemana denk gelir
        filtre_verisi = veri[secim_indexi]
        if secilen_filtre > 3 and onceki_gun_verisi:
            veri_y.append(filtre_verisi - onceki_gun_verisi)
        else:
            veri_y.append(filtre_verisi)
        onceki_gun_verisi = filtre_verisi
    grafik_line.set_data(veri_x, veri_y)
    grafik.relim()
    grafik.autoscale_view(True, True, True)
    istatistik_figure.canvas.draw()
    istatistik_figure.canvas.flush_events()



window = tk.Tk()
window.title('Covid19 Statistics')
window.geometry('1030x600')


frame = tk.Frame(window, background="gray80")
frame.grid(row=0, column=0)


label = tk.Label(frame, text="Country Selection", font="Calibri 12", background="gray80")
label.grid(row=0, column=0)


list_ulke = tk.Listbox(frame, width=30, height=25, selectmode="SINGLE", relief="groove", background="gray97", exportselection=0)
list_ulke.grid(row=1, column=0)
list_ulke.bind("<<ListboxSelect>>", ulke_liste_secim_dinleyicisi)
list_ulke.insert(0, *ulkeler)


frame2 = tk.Frame(window, background="gray80")
frame2.grid(row=1, column=0)
label2 = tk.Label(frame2, text="Data Selection", font="Calibri 12", background="gray80")
label2.grid(row=0, column=0)


list_data = tk.Listbox(frame2, width=30, height=8, selectmode="SINGLE", relief="groove", background="gray97", exportselection=0)
list_data.bind("<<ListboxSelect>>", data_filtre_secim_dinleyicisi)
list_data.insert(0, *covid_durum_list)
list_data.grid(row=1, column=0)


frame3 = tk.Frame(window, background="gray97")
frame3.grid(row=0, rowspan=3, column=1, columnspan=5, padx=10, sticky='wesn')


frame5 = tk.Frame(window)
frame5.grid(row=0, rowspan=2, column=3, columnspan=5)


frame_baslik = tk.Frame(window, background="gray97", padx=20, pady = 34)
frame_baslik.grid(row=0, rowspan=3, column=1, columnspan=5)
label_baslik = tk.Label(frame_baslik,
                        text="Welcome to COVID-19 Dashboard",
                        font="Calibri 24",
                        background="gray80",
                        anchor="center",
                        fg="navy",
                        width=50,
                        height=2,
                        border=3,
                        relief="raised"
                        )
label_baslik.grid(row=0, column=0, columnspan=2)


foto_baslik = tk.PhotoImage(file="covid.png")
foto_baslik= foto_baslik.subsample(2, 2)
foto_baslik_label = tk.Label(frame_baslik, image=foto_baslik,  padx=20)
foto_baslik_label.grid(row=1, column=0)


istatistik_figure = plt.figure(dpi=120)
grafik = istatistik_figure.add_subplot(1, 1, 1)

# grafik.xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
grafik.xaxis.fmt_xdata = dates.DateFormatter('%Y-%m-%d')
istatistik_figure.autofmt_xdate(rotation=45)   #tarih etiketlerinin çakışmasını engeller
grafik.xaxis.set_major_locator(dates.WeekdayLocator(byweekday=MO))

baslangic_tarihi = date(2019, 12, 17)
bitis_tarihi = date(2020, 6, 27)
tarih_araligi = daterange(baslangic_tarihi, bitis_tarihi)
tarih_listesi = []
for tarih in tarih_araligi:
    tarih_listesi.append(tarih.strftime("%Y-%m-%d"))
bos_veri = [0] * len(tarih_listesi)


grafik_line, = grafik.plot(tarih_listesi,
                           bos_veri,
                           color='mediumblue',
                           linestyle="--",
                           linewidth=2,
                           marker="o",
                           markerfacecolor="lightsteelblue",
                           markersize=8,
                           markeredgecolor="blue"
                           )
plt.grid(linestyle="--", alpha=0.4, color="dimgrey", linewidth=1) #ızgara özellikleri
plt.title("COVID-19 Dashboard", color="dodgerblue", fontsize=15, fontweight='bold')
plt.xlabel("Tarih", fontsize=12, fontweight='bold', color="dimgrey")
plt.ylabel("Sayı", fontsize=12, fontweight='bold', color="dimgrey")


canvas = FigureCanvasTkAgg(istatistik_figure, frame5)
canvas.get_tk_widget().grid(row=0, column=0)
frame3.grid_forget()
frame5.grid_forget()


foto = tk.PhotoImage(file="covid19.png")
foto= foto.subsample(2, 2)
fotolabel = tk.Label(frame3, image=foto)
fotolabel.grid(row=1, column=0)

window.mainloop()
