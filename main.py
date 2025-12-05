import sys
import paramiko
import time
import getpass
import os
from paramiko.ssh_exception import AuthenticationException
from tkinter import filedialog
from datetime import datetime


def skan(channel, tgi_f='', debers='debers00008'):
    """Czytamy zwrot, jeśli pojawi się znak zachęty polecenie zwróciło"""
    x = ''
    while True:
        y = channel.recv(9999).decode('utf-8')
        x += y
        if x.count('{}@{}'.format(tgi_f, debers)) or x.count('bash-2.03$'):
            break
        time.sleep(0.05)
    print(x)

def test_poprawnosci_polecenia(channel, tgi, debers):
    """Po odpaleniu każdego skryptu sprawdzamy zmienną $?, czy ma wartość '1'"""
    channel.send('echo $?\n')
    zwrot = skan_zwrot(channel, tgi, debers)
    lista = zwrot.split('\r\n')
    print(lista)


def skan_zwrot(channel, tgi='', debers='debers00008', ciag_znakow='', haslo='', potw=False):
    """Skan i zwrot z terminala. Liczniki są po to, żeby nie wysyłać po kilka razy komend"""
    string = ''

    licznik = 0
    licznik_passwd = 0
    licznik_log = 0
    licznik_prod = 0

    while True:
        y = channel.recv(9999).decode('utf-8')
        print(y)
        string = string + y
        if string.count('{}@{}'.format(tgi, debers)) or string.count('bash-2.03$'):
            break

        if licznik_prod == 0 and  string.count('Y[=default]/N)'):
            channel.send('\n'.encode())
            licznik_prod += 1

        if licznik_log == 0 and string.count('Y/N[=default])'):
            channel.send('\n'.encode())
            licznik_log += 1

        if ciag_znakow != '':
            if potw:
                if string.count(ciag_znakow) and licznik == 0:
                    time.sleep(0.1)
                    channel.send('y\n'.encode())
                    licznik += 1
            else:
                if string.count(ciag_znakow) and licznik == 0:
                    time.sleep(0.1)
                    channel.send('\n'.encode())
                    licznik += 1
        if haslo != '':
            if string.count("password:") == 1 and licznik_passwd == 0:
                time.sleep(0.1)
                channel.send(f'{haslo}\n')
                licznik_passwd += 1
            elif string.count("password:") == 2 and licznik_passwd == 1:
                time.sleep(0.1)
                channel.send(f'{haslo}\n')
                licznik_passwd += 1
            elif string.count("password:") == 3 and licznik_passwd == 2:
                time.sleep(0.1)
                channel.send(f'{haslo}\n')
                licznik_passwd += 1
        time.sleep(0.05)
    return string


def nawiazanie_polaczenia(ip, user, passw, debers=''):
    """Nawiązywanie polączenia z określonym hostem
    debers jest jako argument po to, żeby przesłać do funkcji, skan()
    kiedy znak zachęty składa się z loginu i nazwy hosta"""
    host = ip
    username = user
    password = passw
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, username=username, password=password, port=22)
    except TimeoutError:
        print('\nNie znaleziono hosta {}\n'.format(host))
        input('Naduś coś żeby wyjść\n')
        client.close()
        sys.exit()
    except AuthenticationException:
        print('\nBłędne dane logowania\n')
        input('Naduś coś żeby wyjść\n')
        client.close()
        sys.exit()

    channel = client.invoke_shell(width=300, height=5)
    skan(channel, user, debers)

    return client, channel


def usuwanie_obrazow(channel, tgi, debers):
    """Usuwanie obrazow z folderów"""

    for folder in ['rbc', 'his_rbc']:
        channel.send(f'cd /home/{tgi}/tmp/{folder}/\n'.encode())
        skan(channel, tgi, debers)
        channel.send(f'rm -f *.iso\n'.encode())
        skan(channel, tgi, debers)

    input("Czekam")

def wrzucanie_plikow(conn, tgi, lista, katalog_, sciezka):
    """Wrzucanie plikow z katalogu rbc do katalogu nowo utworzonego, usuwanie przedrostków przed @"""

    sciezka = "/".join([sciezka, '00_ctc/rbc/01/config'])
    print(f"\nPresyłanie plików RBC...")
    with conn.open_sftp() as sftp:
        for plik in lista:
            path = f'{sciezka}/{plik}'
            plik_przyciety = plik.split('@')[1]
            remothe_path = f"/home/{tgi}/{katalog_}/{plik_przyciety}"

            sftp.put(path, remothe_path)


def wrzucanie_plikow_do_cc(conn, tgi, sciezka):
    """Wrzucamy przez sftp pliki na serwer debers00008"""

    remote_path = f"/home/{tgi}/project_data/poland"
    sftp = conn.open_sftp()

    try:
        katalog_linia = sciezka.split('poland/')[1]
    except IndexError:
        _ = input('Nie znaleziono katalogu poland. Naciśnij coś żeby wyjść.')
        sys.exit()
    try:
        sftp.mkdir(remote_path + '/' + katalog_linia)
    except OSError:
        _ = input(f'Katalog {katalog_linia} już istnieje lub nie udało się go stworzyć. Naciśnij coś żeby wyjść.')
        sys.exit()

    print(f"\nPresyłanie plików do /home/{tgi}/project_data/poland/...")

    with sftp:
        for (sci, katalogi, pliki) in os.walk(sciezka):

            if katalogi:
                for katalog in katalogi:
                    path_cc = remote_path + '/' +  sci.split('poland/')[1]
                    path = f'{path_cc}/{katalog}'
                    path = path.replace('\\', '/')

                    try:
                        sftp.mkdir(path)
                    except OSError:
                        _ = input(f'Katalog {katalog_linia} już istnieje lub nie udało się go stworzyć. '
                                  f'Naciśnij coś żeby wyjść.')

                if sci.endswith('00_ctc/rbc/01') or sci.endswith('00_ctc/his_rbc'):
                    katalog_image = '/'.join([path, 'image'])
                    try:
                        sftp.mkdir(katalog_image)
                    except OSError:
                        _ = input(f'Katalog {katalog_image} już istnieje lub nie udało się go stworzyć. '
                                  f'Naciśnij coś żeby wyjść.')

            if pliki:
                for plik in pliki:
                    try:
                        remote_path_cc = '/'.join([remote_path, sci.split('poland/')[1].replace('\\', '/'), plik])
                    except IndexError:
                        print('\nWybrana ścieżka nie zawiera katalogu poland')
                        _ = input('Naciśnij coś żeby wyjść.')
                        sys.exit()
                    #print(f"Wrzucam {plik}")
                    sci_do_pliku = '/'.join([sci, plik])
                    sftp.put(sci_do_pliku, remote_path_cc)



def spr_sciezek(sciezka: str, kontynuacja: str, licznik : int) -> int:
    lista : list = kontynuacja.split("/")

    try:
        zwrot: list = os.listdir(os.path.join(sciezka, *lista))
        if len(zwrot) == 0:
            licznik += 1
            print(f'\nBrak plików w scieżce {kontynuacja}')
    except FileNotFoundError:
        licznik += 1
        print(f"Brak katalogu {kontynuacja}")

    return licznik


def katalog_wybor():
    """Określanie ścieżki i sprawdzanie struktury katalogów"""
    sciezka_init = filedialog.askdirectory(title='Wybór katalogu linii dla danego projektu')

    if not sciezka_init:
        sys.exit()
    licznik = 0
    licznik = spr_sciezek(sciezka_init, '/00_ctc/rbc/01/config', licznik)
    licznik = spr_sciezek(sciezka_init, '/00_ctc/his_rbc', licznik)

    # Sprawdzanie poprawności struktury plików
    for (sciezka, katalogi, pliki) in os.walk(sciezka_init):
        #print(sciezka)
        if sciezka.count('.doc') and katalogi and pliki:
            for x in pliki:
                if x.endswith(".pdf"):
                    print("W katalogu .doc są pliki .pdf, do poprawy.")
                    licznik += 1

        if sciezka.count(".dmt") and pliki:
            ilosc = len(pliki)
            if ilosc > 1:
                print("\nW katalogu 00_ctc/.dmt jest więcej niż jeden plik, do poprawy.")
                licznik += 1
            elif ilosc == 0:
                print("Brak plików w katalogu 00_ctc/.dmt, do poprawy.")
                licznik += 1
            elif ilosc == 1:
                if pliki[0].endswith('.7z') or pliki[0].endswith('.mdb'):
                    print("\nZłe rozszerzenie pliku bazodanowego. Jest 7z, powinno być zip.")

        if sciezka.count(r'\00_ctc\rbc\01\config'):
            if len(pliki) != 8:
                print("\nW katalogu rbc/01/config powinno być 8 plików, do poprawy")
                licznik += 1
            elif len(pliki) == 8:
                lista_potrzebnych = ['AURData.xml', 'Coor_STR.xml', 'Location', 'STR.xml', 'SafeLocationData.xml',
                                     'data.md5', 'hosts', 'ocs.specific.conf']
                lista_przycietych = [x.split('@')[1] for x in pliki]
                for plik in lista_potrzebnych:
                    if plik not in lista_przycietych:
                        print(f"W katalogu rbc brakuje pliku {plik}, do poprawy.")
                        licznik += 1

        if sciezka.count(r'\00_ctc\his_rbc') and pliki and katalogi:
            lista_opr = [x for x in katalogi if x.count("opr")]
            if len(lista_opr) == 0:
                print("\nBrak katalogów opr")
            elif len(lista_opr) > 1:
                katalog_opr = os.path.join(sciezka, lista_opr[0], 'config')
                zawartosc_pliku = os.listdir(katalog_opr)
                plik_models = [x for x in zawartosc_pliku if x.count('models')]
                sciezka_do_models = os.path.join(katalog_opr, plik_models[0])
                with open(sciezka_do_models, 'r') as f:
                    lista_models = list(f)
                lista_stacji = []
                for linia in lista_models:
                    if linia.count("<model>"):
                        stacja = linia.split("\\")[0].replace(" <model>", "")
                        if stacja not in lista_stacji and stacja != '00_ctc':
                            lista_stacji.append(stacja)

                for stacja in lista_stacji:
                    try:
                        zwrot = os.listdir(os.path.join(sciezka_init, stacja))
                        if len(zwrot) != 2:
                            print(f"\nBrak katalogów w {stacja}, do poprawy.")
                        elif len(zwrot) == 2:
                            try:
                                zwrot = os.listdir(os.path.join(sciezka_init, stacja, 'his_rbc'))
                                if len(zwrot) != 2:
                                    print(f'\nBrak katalogów w {stacja}/his_rbc, do poprawy.')
                                    licznik += 1
                            except FileNotFoundError:
                                print(f"\nBrak katalogu {stacja}/his_rbc")
                                licznik += 1

                            try:
                                zwrot = os.listdir(os.path.join(sciezka_init, stacja, 'im/01/config'))
                                if len(zwrot) != 1:
                                    print(f'\nBrak pliku elem.dat w {stacja}/im/01/config, do poprawy.')
                                    licznik += 1
                            except FileNotFoundError:
                                print(f"\nBrak katalogu {stacja}/im/01/config")
                                licznik += 1

                    except FileNotFoundError:
                        print(f"\nBrak katalogu stacyjnego {stacja}, do poprawy.")
                        licznik += 1

    if licznik > 0:
        input("\nSą rzeczy do poprawy. Naciśnij coś żeby wyjść i poprawić.")
        sys.exit()

    return sciezka_init

def pliki_rbc(sciezka : str) -> list:
    sciezka = '/'.join([sciezka, '00_ctc/rbc/01/config'])
    lista = os.listdir(sciezka)

    return lista


def sprawdzanie_zawartosci_rbc(lista):
    """Spr. czy mamy wszystkie pliki"""

    if len(lista) != 8:
        return False

    lista_potrzebnych = ['AURData.xml', 'Coor_STR.xml', 'Location', 'STR.xml', 'SafeLocationData.xml',
                         'data.md5', 'hosts', 'ocs.specific.conf']
    licznik = 0
    for plik in lista:
        try:
            if plik.split('@')[1] in lista_potrzebnych:
                licznik += 1
        except IndexError:
            pass

    if licznik == 8:
        return True
    else:
        return False


def init_prod_repo(rbc_prod_conn_init, channel, tgi, katalog_init):
    """Uruchamiamy skrypt initProdRepo"""
    channel.send(f"/usr/atria/bin/cleartool setview {tgi}_rbcprod\n".encode())
    skan(channel)
    channel.send(f"cd /cc/rbc/Production/bin\n".encode())
    skan(channel)



    print("\nOdpalam initProdRepo...")
    channel.send(f"initProdRepo -setview -cae {katalog_init} -src /home/{tgi}/{katalog_init} PKP.1.3.2.0 02\n".encode())
    zwrot = skan_zwrot(channel)
    if zwrot.count('incorrect parameters'):
        input('\nCoś nie tak z initProdRepo, naciśnij coś żeby zobaczyć loga')
        print(zwrot)
        channel.close()
        rbc_prod_conn_init.close()
        sys.exit()
    print('\ninitProdRepo OK\n')


def configure_all(rbc_prod_conn_init, channel):
    """Uruchamianie skryptów 'configureAll' i 'collectUserData'"""
    print("\nOdpalam configureAll...")
    channel.send(f"configureAll customer\n".encode())
    zwrot_configure = skan_zwrot(channel)
    if not zwrot_configure.count('successful.'):
        _ = input("\nCoś nie tak z configureAll, naciśnij coś żeby zobaczyć loga.")
        print(zwrot_configure)
        zamykanie_polaczenia(rbc_prod_conn_init, channel)
        sys.exit()
    print('\nconfigureAll OK')

    print('\nOdpalam collectUsedData...')
    channel.send(f"collectUsedData customer\n".encode())
    _ = skan_zwrot(channel, ciag_znakow='Return only.')  # Nie ma co sprawdzać
    print('\ncollectUsedData OK')
    print('Odpalam ConfgDataRBC2Pdf ...')
    channel.send('cd; ConfigDataRBC2Pdf.sh DataProd.xml\n'.encode())
    zwrot_pdf = skan_zwrot(channel)
    if not zwrot_pdf.count('DataProd.xml transformed to DataProd.pdf'):

        _ = input("\nCoś nie tak z ConfigDataRBC2, naciśnij coś żeby zobaczyć loga.")
        print(zwrot_configure)
        zamykanie_polaczenia(rbc_prod_conn_init, channel)
        sys.exit()

    print('\nConfgDataRBC2Pdf OK')
    channel.send('exit\n'.encode())
    skan(channel)
    channel.send('exit\n'.encode())
    skan(channel)


def katalog_roboczy(channel):
    while True:
        katalog = input('\nPodaj nazwę katalogu roboczego do wrzucenia danych RBC: ')
        if not tworzenie_katalogu_rbc(channel, katalog).count('mkdir: Failed'):
            print(f"Utworzono katalog {katalog}")
            break
        else:
            print(f"\nKatalog {katalog} już istnieje.")
    return katalog


def tworzenie_katalogu_rbc(channel, katalog_nowy):
    """Tworzenie katalogu w katalogu domowym"""
    channel.send(f"mkdir {katalog_nowy}\n".encode())
    return skan_zwrot(channel)


def create_cd(conn, channel, login, haslo='', debers=''):
    """Tworzenie obrazu createCDs"""
    print("\nOdpalanie skryptu CreateCDs...")
    channel.send("cd /local/CD_3.3.6/bin\n".encode())
    skan(channel, login, debers)
    channel.send(f"sudo ./createCDs -aur {login} debersuwg-rbcprod1\n".encode())
    zwrot = skan_zwrot(channel, login, debers, 'Press any key to continue ...', haslo)

    if not zwrot.count('was generated'):
        print(zwrot)
        _ = input("\nCoś poszło nie tak z ")
        zamykanie_polaczenia(conn, channel)

    print("\nCreateCDs OK")
    lista_zwrot = zwrot.split('\r\n')
    return lista_zwrot[-4].strip()


def import_danych_do_cc(channel, debers,  login,  linia, etykieta, preview):
    """Importowanie wszystkich danych do CC"""
    channel.send('cd /cc/l905/customer/poland \n'.encode())
    skan(channel, login, debers)
    zwrot = ''
    if preview:
        channel.send(f"clearfsimport -nsetevent -recurse -preview /home/{login}/project_data/poland/{linia} .\n".encode())
        skan_zwrot(channel, login, debers)
        return zwrot
    else:
        channel.send(
            f"clearfsimport -nsetevent -recurse -identical -mklabel {etykieta} /home/{login}/project_data/poland/{linia} .\n".encode())
        skan_zwrot(channel, login, debers)
        return None

def zamykanie_polaczenia(conn, channel):
    """Zamykamy połączenie z hostem"""
    conn.close()
    channel.close()

def etykieta_cc():
    """Określanie etykiety do CC"""
    while True:
        etykieta = input("\nPodaj etykietę: ")
        potw = input(f"Etykieta to {etykieta}, zgadza się?[T/N]: ").upper()
        if potw == 'T':
            zwrot = etykieta
            break
    return zwrot

def linia_cc(linia, przelacznik = True):
    """Określanie katalogu linii do CC"""
    while True:
        if przelacznik:
            decyzja = input(f"\nCzy {linia} to katalog linii do importu plików do CC?[T/N]: ").upper()
        else:
            decyzja = 'N'

        if decyzja == 'T':
            zwrot = linia
            break
        elif decyzja == 'N':
            while True:
                linia_zwrot = input("\nPodaj katalog linii: ")
                potw = input(f"\nKatalog linii to {linia_zwrot}, zgadza się?[T/N]: ").upper()
                if potw == 'T':
                    zwrot = linia_zwrot
                    break
            break
    return zwrot

def weryfikacja_etykiety(channel, etykieta, login):
    channel.send('cd /cc/l905/customer/poland\n'.encode())
    skan_zwrot(channel, login, 'debers00008')
    channel.send(f'ct mklbtype -nc {etykieta}\n'.encode())
    zwrot = skan_zwrot(channel, login, 'debers00008')

    if zwrot.count('already exists'):
        return False
    else:
        return True


def weryfikacja_linii(channel, linia, login):
    channel.send(f'cd /cc/l905/customer/poland/{linia}\n'.encode())
    zwrot = skan_zwrot(channel, login, 'debers00008')

    if zwrot.count('No such file or directory'):
        return False
    else:
        return True

def sprawdzanie_import_preview(zwrot : str, conn, channel):
    lista = zwrot.split('\r\n')
    lista_element = []
    for l in lista:
        if l.count(' element'):
            lista_element.append(l)

    if len(lista_element) != 0:
        print("\nLista nowych plików:")
        for elem in lista:
            print(elem)

        while True:
            zwrotka = input("\nCzy tak ma być?[T/N]: ").upper()
            if zwrotka == 'T':
                break
            elif zwrotka == 'N':
                _ = input("\nTo do poprawy. Naciśnij coś żeby wyjść.")
                zamykanie_polaczenia(conn, channel)
                sys.exit()
            else:
                print("\nBłędny wybór, powinno być T lub N.")


def czyt_istniejacego_edcs(channel, tgi, debers):
    """Czytamy isniejące rov dla potomności"""

    channel.send('cd /cc/l905/customer/poland\n'.encode())
    skan(channel, login_abbr, 'debers00008')

    channel.send('ct catcs\n')
    zwrot = skan_zwrot(channel, tgi, debers)

    lista = zwrot.split('\r\n')

    return lista[1:-1]

def zapisywanie_istniejacego_edcs(conn, tgi, lista):
    """Zapisywanie rov dla potomności w katalogu roboczym"""
    #TODO na później, zróbmy to bezpośrednio na CC
    lista = [x + '\n' for x in lista]
    with open('edcs_historia.txt', 'a', newline='') as f:

        f.write('\n\n')
        f.write(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        f.write('\n')
        f.writelines(lista)

    with open('edcs_aktualny.txt', 'w', newline='') as f:
        f.writelines(lista)

    time.sleep(1)
    remote = f'/home/{tgi}/tmp/edcs_aktualny.txt'
    #print("Sciezka ", remote)
    with conn.open_sftp() as sftp:
        sftp.put('edcs_aktualny.txt', remote)

def ustawianie_edcs_do_importu(channel, tgi, debers):
    """Ustawiamy rov dla importu plików"""
    #lista = ('element * CHECKEDOUT\n', 'element * /main/LATEST/')
    nazwa_pliku = 'edcs_import.txt'
    channel.send(f'echo "element * CHECKEDOUT" > /home/{tgi}/tmp/{nazwa_pliku}\n'.encode())
    skan(channel, tgi, debers)
    channel.send(f'echo "element * /main/LATEST/" >> /home/{tgi}/tmp/{nazwa_pliku}\n'.encode())
    skan(channel, tgi, debers)
    channel.send(f'ct setcs /home/{tgi}/tmp/{nazwa_pliku}\n'.encode())
    skan(channel, tgi, debers)

def ustawienie_oryginalnego_edcs(channel, tgi, debers):
    channel.send(f'ct setcs /home/{tgi}/tmp/edcs_aktualny.txt\n'.encode())
    skan(channel, tgi, debers)

def kopiowanie_data_prod_pdf(conn, channel, tgi, haslo):
    """Kopiowanie DataProd.pdf na tmp w debers00008"""
    channel.send('cd\n'.encode())
    skan(channel)
    print("\nKopiuję DataProd.pdf do tpm na debers00008.\n")
    channel.send(f'scp DataProd.pdf {tgi}@debers00008:/home/{tgi}/tmp/rbc\n'.encode())
    zwrot = skan_zwrot(channel, debers='XXX', haslo=haslo) # XXX bo dałem debers00008 jako default a to łapie za wcześnie, XXX jest fejkowe
    if zwrot.count("No such file or directory"):
        _ = input("Nie mogę znależć DataProd.pdf. Naciśnij coś żeby wyjść.")
        zamykanie_polaczenia(conn, channel)
        sys.exit()

def kopiowanie_rbc_iso(conn, channel, tgi: str, tgi_abbr: str, debers: str, haslo: str, folder: str):
    """Sprawdzamy, czy obrazy iso się stworzyły i kopiujemy do katalogu home/<tgi>/tmp"""

    print('\nKopiowanie obrazów .iso do tpm na debers00008...')
    channel.send(f'cd {folder}\n'.encode())
    skan(channel, tgi, debers)
    channel.send('ls -l\n'.encode())
    zwrot = skan_zwrot(channel, tgi, debers)
    lista = zwrot.split('\r\n')[2:-2]

    lista_data_elem = [[x.split('\x1b[00m')[0].split(' ')[-3:-1], x.split('\x1b[00m')[1]] for x in lista]

    lista_iso = [x[1] for x in lista_data_elem if (x[1].endswith('FCdump.iso') or x[1].endswith('OMS.iso')
                                           or x[1].endswith('RBCAUR.iso'))]

    if len(lista_iso) == 3:

        while True:
            channel.send(f'scp *.iso {tgi_abbr}@debers00008:/home/{tgi_abbr}/tmp/rbc\n'.encode())
            zwrot = skan_zwrot(channel, tgi, debers='debersuxvl03', haslo=haslo)

            if zwrot.count('Quota') or zwrot.count('quota'):
                _ = input(f"\nBrakuje miejsca na /home/{tgi_abbr}/tmp/. Zwolnij miejsce i naciśnij coś żeby kontynuować.")
            elif zwrot.count('No such file or directory'):
                _ = input(f'\nNie ma obrazów w katalogu {folder}. Naciśnij coż żeby wyjść.')
                zamykanie_polaczenia(conn, channel)
            else:
                break

    else:
        _ = input('\nObrazy .iso RBC nie wygenerowały się poprawnie. Naciśnij coś żeby wyjść')
        zamykanie_polaczenia(conn, channel)
        sys.exit()

    print('\nOk, kopiowanie zakończone.')


def edcs_his_rbc(linia, etykieta_sys, etykieta):
    lista = ['element * CHECKEDOUT', '', '#================================================',
             '# first see all root directories',
             'element -directory /cc/lci/estw_l90_5                                   /main/LATEST',
             'element -directory /cc/tas/tagopert                                     /main/LATEST',
             '#================================================', '',
             '#================================================', '# SCRIPTS',
             'element -directory  /cc/lci/estw_l90_5/estw                             /main/LATEST',
             'element -directory  /cc/lci/estw_l90_5/estw/common                      /main/LATEST',
             'element -directory  /cc/lci/estw_l90_5/estw/common/tool                 /main/LATEST',
             'element -directory  /cc/lci/estw_l90_5/estw/common/tool/scripts         /main/LATEST',
             'element /cc/lci/estw_l90_5/estw/common/tool/scripts/...                 /main/LATEST',
             '#================================================', '',
             '#================================================', '# HIS Data PKP',
             f'element -dir /cc/l905/customer/poland                                          {etykieta}',
             f'element -dir /cc/l905/customer/poland/{linia}                                  {etykieta}',
             f'element -dir /cc/l905/customer/poland/{linia}/00_ctc                           {etykieta}',
             f'element -dir /cc/l905/customer/poland/{linia}/.doc                              -none',
             f'element -dir /cc/l905/customer/poland/{linia}/00_ctc/his_rbc                   {etykieta}',
             f'element -dir /cc/l905/customer/poland/{linia}/00_ctc/his_rbc/image              -none',
             f'element /cc/l905/customer/poland/{linia}/his_rbc/...                           {etykieta}',
             f'element -dir /cc/l905/customer/poland/{linia}/*                                {etykieta}',
             f'element -dir /cc/l905/customer/poland/{linia}/*/his_rbc                        {etykieta}',
             f'element /cc/l905/customer/poland/{linia}/*/his_rbc/...                         {etykieta}', '',
             '#================================================', '# Diagnosis Catalogues Baseline PL 2.3.0.2',
             f'element -dir /cc/l905/customer/poland/.diagnosis                        {etykieta_sys}',
             f'element /cc/l905/customer/poland/.diagnosis/COMMON_Severities.xml       {etykieta_sys}',
             f'element /cc/l905/customer/poland/.diagnosis/DiagCatHIS_RBC.xml          {etykieta_sys}',
             f'element /cc/l905/customer/poland/.diagnosis/DiagCatRBC.xml              {etykieta_sys}',
             'element /cc/l905/customer/poland/.diagnosis/...                         -none', '',
             '#================================================', '# Target System',
             'element -dir /cc/his_rbc/his_rbc                                                        /main/LATEST',
             'element -dir /cc/his_rbc/his_rbc/icd_buildenv                                           /main/LATEST',
             'element -dir /cc/his_rbc/his_rbc/icd_buildenv/rpmbuild                                  /main/LATEST',
             'element -dir /cc/his_rbc/his_rbc/icd_buildenv/rpmbuild/SOURCES                          /main/pkp/LATEST',
             'element /cc/his_rbc/his_rbc/icd_buildenv/rpmbuild/SOURCES/HIS_RBC_CAE_PKP_data.zip      /main/LATEST',
             '#================================================', '', '#================================================',
             '# UTILS', 'element /cc/tag/gnutil/...                                              IM_GNUTIL_02',
             'element /cc/tag/mt/...                                                  MT_1.8.1',
             '#================================================', '',
             'element *                                                               -none']

    return lista

def edcs_his_rbc_build(linia : str, etykieta_sys : str, etykieta : str)-> list[str]:

    lista = ['element * CHECKEDOUT', f'element * {etykieta_sys}', '',
             '#finaler Speicherplatz fuer das Image',
             'element -dir /cc/l905/customer/poland                                                /main/LATEST',
             f'element -dir /cc/l905/customer/poland/{linia}                                         /main/LATEST',
             f'element -dir /cc/l905/customer/poland/{linia}/00_ctc                                     /main/LATEST',
             f'element -dir /cc/l905/customer/poland/{linia}/00_ctc/his_rbc                             /main/LATEST',
             f'element /cc/l905/customer/poland/{linia}/00_ctc/his_rbc/image/...                        /main/LATEST',
             '', f'element * {etykieta}']

    return lista

def zapisywanie_edcs_his_rbc(channel, tgi, lista, nazwa):
    """Wpisujemy do tmp/edcs_his_rbc"""
    licznik = 1
    for linia in lista:
        if licznik == 1:
            channel.send(f'echo "{linia}" > /home/{tgi}/tmp/{nazwa}\n'.encode())
            skan(channel, tgi, 'debersuxv045')
        else:
            channel.send(f'echo "{linia}" >> /home/{tgi}/tmp/{nazwa}\n'.encode())
            skan(channel, tgi, 'debersuxv045')
        licznik += 1

    channel.send(f'ct setcs /home/{tgi}/tmp/{nazwa}\n'.encode())
    skan(channel, tgi, 'debersuxv045')

def data_pack_his_rbc(conn, channel, tgi, debers, etykieta):
    print('\nOdpalam skrypt mkDataPackHISRBC ...')
    channel.send('/cc/lci/estw_l90_5/estw/common/tool/scripts/mkDataPackHISRBC.sh -c poland\n'.encode())
    zwrot = skan_zwrot(channel, tgi, debers)

    if zwrot.count('Exit this script'):
        _ = input('\nCoś nie tak ze skryptem mkDataPackHISRBC. Naciśnij coś żeby zobaczyć loga i wyjść')
        print(zwrot)
        zamykanie_polaczenia(conn, channel)
        sys.exit()

    print('\nmkDataPackHISRBC ok.')

    channel.send('cd /cc/his_rbc/his_rbc/icd_buildenv/\n'.encode())
    skan(channel, tgi, debers)

    channel.send(f'ct mklbtype -nc {etykieta}\n'.encode())
    skan(channel, tgi, debers)

    channel.send('ct ci -nc /cc/his_rbc/his_rbc/icd_buildenv/rpmbuild/SOURCES/HIS_RBC_CAE_PKP_data.zip\n'.encode())
    skan(channel, tgi, debers)

    channel.send(f'ct mklabel -nc {etykieta} /cc/his_rbc/his_rbc/icd_buildenv/rpmbuild/SOURCES/HIS_RBC_CAE_PKP_data.zip\n'.encode())
    skan(channel, tgi, debers)

def mk_inst_cd(conn, channel, tgi, debers, etykieta):
    print('\nOdpalam skrypt mkInstCD ...')
    channel.send('cd /cc/his_rbc/his_rbc/icd_buildenv/\n'.encode())
    skan(channel, tgi, debers)

    channel.send(f'./mkInstCD.sh -l {etykieta}\n'.encode())
    zwrot  = skan_zwrot(channel, tgi, debers)

    if not zwrot.count('SUCC: all done'):
        _ = input('\nCoś poszło nie tak z robieniem obrazu his_rbc .iso. Naciśnij coś, żeby zobaczyć loga i wyjść')
        print(zwrot)
        zamykanie_polaczenia(conn, channel)

    print("mkInstCD OK.\n")

def kopiowanie_his_rbc(conn, channel, tgi, debers, etykieta, haslo):
    print("\nKopiowanie obrazu his_rbc do tmp na debers00008 ...")
    while True:
        channel.send(f'scp /cc/his_rbc/his_rbc/icd_buildenv/iso/{etykieta}.iso {tgi}@debers00008:/home/{tgi}/tmp/his_rbc/\n'.encode())
        zwrot = skan_zwrot(channel, tgi, debers, haslo=haslo)

        if zwrot.count('Quota') or zwrot.count('quota'):
            _ = input(f"Brakuje miejsca na /home/{tgi}/tmp/. Zwolnij miejsce i naciśnij coś żeby kontynuować.")
        elif zwrot.count('No such file or directory'):
            _ = input(f'Nie ma obrazu {etykieta}.iso w katalogu ...icd_buildenv/iso/. Naciśnij coż żeby wyjść.')
            zamykanie_polaczenia(conn, channel)
            sys.exit()
        else:
            break

    print("\nKopiowanie zakończone.\n")


def zawartosc_folderu(channel, tgi, debers, sciezka):
    """"""
    channel.send(f'cd {sciezka}\n'.encode())
    skan(channel, tgi, debers)

    channel.send('ls -l\n'.encode())
    zwrot = skan_zwrot(channel, tgi, debers)
    lista_tmp = zwrot.split('\r\n')[1:-1]

    lista_data_elem = [x.split(' ')[-1] for x in lista_tmp]
    print(lista_data_elem)
    input("Czekam")
    return lista_data_elem


def import_obrazow_na_cc(conn, channel, tgi, etykieta, debers, linia):
    """Importa obrazow na cc."""

    while True:
        przedrostek_stacji = input('Wprowadź przedrostek linii do obrazów .iso (pl_<przedrostek>@): ')
        potw = input(f'Wprowadzony przedrostek to: {przedrostek_stacji}, zgadza się? [T/N]')
        if potw == 'T':
            break
        elif potw == 'N':
            pass
        else:
            print("Błędny wybór pownno być T/N.")

    prefix = f'pl_{przedrostek_stacji}@'

    lista_data_elem = zawartosc_folderu(channel, tgi, debers, f'/home/{tgi}/tmp/rbc/')

    #Zmiana nazw rbc .iso
    lista_iso = [x for x in lista_data_elem if not x.startswith('pl_') and (x.endswith('FCdump.iso') or x.endswith('OMS.iso') or x.endswith('RBCAUR.iso'))]

    if len(lista_iso) != 3:
        _ = input('Brak obrazów w katalogu tmp/rbc. Naciśnij coś żeby wyjść.')
        zamykanie_polaczenia(conn, channel)
        sys.exit()

    lista_prefix_iso = []
    for elem in lista_iso:
        channel.send(f'mv ./{elem} ./{prefix+elem}\n')
        _ = skan_zwrot(channel, tgi, debers, ciag_znakow=".iso'?", potw=True)
        lista_prefix_iso.append(prefix+elem)

    #Zmiana nazwy his_rbc
    lista_data_elem_his_rbc = zawartosc_folderu(channel, tgi, debers, f'/home/{tgi}/tmp/his_rbc/')

    try:
        elem_his_rbc_iso = [x for x in lista_data_elem_his_rbc if x.startswith('DATA') and x.endswith('.iso')][0]
    except IndexError:
        _ = input('W tmp brak obrazu his_rbc. Naciśnij coś żeby wyjść.')
        zamykanie_polaczenia(conn, channel)
        sys.exit()

    zmieniona_nazwa_obrazu_his_rbc = prefix + 'his_rbc.iso'

    channel.send(f'mv {elem_his_rbc_iso} {zmieniona_nazwa_obrazu_his_rbc}\n')
    skan(channel, tgi, debers)

    # Import rbc.iso
    channel.send(f'cd /cc/l905/customer/poland/{linia}/00_ctc/rbc/01/image\n'.encode())
    zwrot = skan_zwrot(channel, tgi, debers)
    if zwrot.count('No such file or directory'):
        _ = input(f'Brak ścieżki /cc/l905/customer/poland/{linia}/00_ctc/rbc/01/image. Naciśnij coś żeby wyjść.')
        sys.exit()

    for elem in lista_prefix_iso:
        channel.send(
            f'clearfsimport -nsetevent -recurse -preview -mklabel {etykieta} /home/{tgi}/tmp/rbc/{elem} .\n'.encode())
        skan(channel, tgi, debers)

    channel.send(
        f'clearfsimport -nsetevent -recurse -preview -mklabel {etykieta} /home/{tgi}/tmp/rbc/DataProd.pdf .\n'.encode())
    skan(channel, tgi, debers)

    #Import his_rbc.iso
    channel.send(
        f'clearfsimport -nsetevent -recurse -preview -mklabel {etykieta} /home/{tgi}/tmp/his_rbc/{zmieniona_nazwa_obrazu_his_rbc} .\n'.encode())
    skan(channel, tgi, debers)



if __name__ == '__main__':
    rbc_prod = '10.220.30.208'
    debersuxvl03 = '10.220.181.133'
    debersuxv045 = '10.220.30.245'  # obraz his_rbc
    debers00008 = '10.220.30.24'
    # debers058 = '10.220.30.98'
    # debers794 = '10.48.71.44'

    sciezka_main = katalog_wybor()

    lista_plikow_rbc = pliki_rbc(sciezka_main)

    linia_main = sciezka_main.split("/")[-1]
    while True:
        login_main = input('\nPodaj login do produkcji obrazu rbc: ')

        if login_main.endswith('rbc'):
            break
        else:
            _ = input("\nPodany login nie jest do konta rbc. Naciśnij coś i podaj jeszcze raz.")

    login_abbr = login_main.split('_')[0]
    haslo_main = getpass.getpass(prompt='Podaj haslo: ')

    print("\nŁączenie z debers0008...")
    debers_08_conn, channel_debers_08 = nawiazanie_polaczenia(debers00008, login_abbr, haslo_main)

    wrzucanie_plikow_do_cc(debers_08_conn, login_abbr, sciezka_main)

    #Przechodzimy do katalogu /tmp i usuwamy obrazy .iso
    usuwanie_obrazow(channel_debers_08, login_abbr, 'debers00008')

    # Czytamy istniejący edcs
    lista_istniejaca_edcs = czyt_istniejacego_edcs(channel_debers_08, login_abbr, 'debers00008')
    zapisywanie_istniejacego_edcs(debers_08_conn, login_abbr, lista_istniejaca_edcs)

    # Ustawiamy edcs do importu
    ustawianie_edcs_do_importu(channel_debers_08, login_abbr, 'debers00008')

    # Określamy i sprawdzamy etykietę
    etykieta_main = etykieta_cc()

    print("\nSprawdzam etykietę ..")
    while True:
        poprawne_etykieta = weryfikacja_etykiety(channel_debers_08, etykieta_main, login_abbr)
        if poprawne_etykieta:
            break
        else:
            print(f'\nEtykieta {etykieta_main} istnieje podaj jeszcze raz')
            etykieta_main = etykieta_cc()

    print(f"\nSprawdzam, czy jest ścieżka z katalogiem linii {linia_main}")

    # Określamy i spr katalog linii
    katalog_linii = linia_cc(linia_main)

    while True:
        poprawne = weryfikacja_linii(channel_debers_08, katalog_linii, login_abbr)
        if poprawne:
            break
        else:
            print(f'\nPodany katalog {katalog_linii} istnieje podaj jeszcze raz')
            etykieta_main = linia_cc(linia_main, przelacznik=False)


    print("\nPreview importu plików ...")
    zwrot_import_preview = import_danych_do_cc(channel_debers_08, 'debers00008', login_abbr,
                                               katalog_linii, etykieta_main, True)

    # TODO sprawdzenie, czy to w ogóle działa
    print("\nSprawdzanie nowych elementów ...")
    sprawdzanie_import_preview(zwrot_import_preview, debers_08_conn, channel_debers_08)

    print("\nImportowanie i etykietowanie ...")
    zwrot_import = import_danych_do_cc(channel_debers_08, 'debers00008', login_abbr, katalog_linii, etykieta_main, False)

    ustawienie_oryginalnego_edcs(channel_debers_08, login_abbr, 'debers00008')

    print("\nZamykanie połączenia do debers00008 ...\n")
    zamykanie_polaczenia(debers_08_conn, channel_debers_08)



    # Polaczenie do rbc prod
    print("\nŁączenie z hostem do produkcji obrazu RBC...")
    rbc_prod_conn, channel_rbc = nawiazanie_polaczenia(rbc_prod, login_main, haslo_main)
    print(f"\nOk, połączono z hostem do produkcji obrazu RBC.")

    # Tworzymy katalog, jeśli już jest pytamy jeszcze raz
    katalog_rbc = katalog_roboczy(channel_rbc)

    # Import plików rbc do rbc_prod
    wrzucanie_plikow(rbc_prod_conn, login_main, lista_plikow_rbc, katalog_rbc, sciezka_main)

    # Uruchamiamy skrypt initProdRepo
    init_prod_repo(rbc_prod_conn, channel_rbc, login_main, katalog_rbc)

    # Uruchamiamy skrypty configAll, collect.., pdf
    configure_all(rbc_prod_conn, channel_rbc)

    kopiowanie_data_prod_pdf(rbc_prod_conn, channel_rbc, login_abbr, haslo_main)

    print("\nZamykanie połączenia z hostem do produkcji obrazu RBC.\n")
    zamykanie_polaczenia(rbc_prod_conn, channel_rbc)


    print("\nŁączenie z hostem debersuxvl03...")
    debersuxvl03_conn, debersuxvl03_channel = nawiazanie_polaczenia(debersuxvl03,
                                                                    login_main, haslo_main, debers='debersuxvl03')
    print(f"\nOk, połączono z debersuxvl03.")

    folder_obraz_rbc = create_cd(debersuxvl03_conn, debersuxvl03_channel, login_main, haslo_main, 'debersuxvl03')

    kopiowanie_rbc_iso(debersuxvl03_conn, debersuxvl03_channel, login_main, login_abbr,'debersuxvl03', haslo_main, folder_obraz_rbc)

    zamykanie_polaczenia(debersuxvl03_conn, debersuxvl03_channel)

    print("\nZamykanie połączenia z hostem debersuxvl03.")

    print("\nŁączenie z hostem debersuxv045...")
    debers045_conn, debers045_channel = nawiazanie_polaczenia(debersuxv045, login_abbr, haslo_main, 'debersuxv045')


    etykieta_systemowa = 'ETCS_RC_1.2_PL2.3.0.2'

    debers045_channel.send('ct setview his_rbc_cupl_copy_data\n'.encode())
    skan(debers045_channel, login_abbr, 'debersuxv045')

    edcs_his_rbc_lista = edcs_his_rbc(linia_main, etykieta_systemowa, etykieta_main)

    zapisywanie_edcs_his_rbc(debers045_channel, login_abbr, edcs_his_rbc_lista, 'edcs_his_rbc')

    data_pack_his_rbc(debers045_conn, debers045_channel, login_abbr, 'debersuxv045', etykieta_main)

    debers045_channel.send('ct setview his_rbc_cupl_build\n'.encode())

    edcs_his_rbc_build_lista = edcs_his_rbc_build(linia_main, etykieta_systemowa, etykieta_main)

    zapisywanie_edcs_his_rbc(debers045_channel, login_abbr, edcs_his_rbc_build_lista, 'edcs_his_rbc_build')

    mk_inst_cd(debers045_conn, debers045_channel, login_abbr, 'debersuxv045', etykieta_main)

    kopiowanie_his_rbc(debers045_conn, debers045_channel, login_abbr, 'debersuxv045', etykieta_main, haslo_main)

    print("\nZamykam połączenie do debersuxv045...")
    zamykanie_polaczenia(debers045_conn, debers045_channel)

    print("\nŁączenie z debers0008...")
    debers_08_conn, channel_debers_08 = nawiazanie_polaczenia(debers00008, login_abbr, haslo_main)

    lista_istniejaca_edcs = czyt_istniejacego_edcs(channel_debers_08, login_abbr, 'debers00008')

    zapisywanie_istniejacego_edcs(debers_08_conn, login_abbr, lista_istniejaca_edcs)

    ustawianie_edcs_do_importu(channel_debers_08, login_abbr, 'debers00008')

    import_obrazow_na_cc(debers_08_conn, channel_debers_08, login_abbr, etykieta_main, 'debers00008', linia_main)

    ustawienie_oryginalnego_edcs(channel_debers_08, login_abbr, 'debers00008')

    print(f'\nWszystkie nowo utworzone obrazy znajdują się w katalogu /home/{login_abbr}/tmp na debers00008.')

    print('\n\n\tFIN.\n')

