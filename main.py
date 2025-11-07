import sys
import paramiko
import time
import getpass
import os
from paramiko.ssh_exception import AuthenticationException
from tkinter import filedialog


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


def skan_zwrot(channel, tgi='', debers='debers00008', ciag_znakow='', haslo=''):
    """Skan i zwrot z terminala. Liczniki są po to, żeby nie wysyłać po kilka razy komend"""
    licznik = 0
    string = ''
    licznik_passwd = 0
    while True:
        y = channel.recv(9999).decode('utf-8')
        print(y)
        string = string + y
        if string.count('{}@{}'.format(tgi, debers)) or string.count('bash-2.03$'):
            break
        if ciag_znakow != '':
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
        print('\n\tNie znaleziono hosta {}\n'.format(host))
        input('Naduś coś żeby wyjść\n')
        client.close()
        sys.exit()
    except AuthenticationException:
        print('\n\tBłędne dane logowania\n')
        input('Naduś coś żeby wyjść\n')
        client.close()
        sys.exit()

    channel = client.invoke_shell(width=300, height=5)
    skan(channel, user, debers)

    return client, channel


def wrzucanie_plikow(conn, tgi, lista, katalog_, sciezka):
    """Wrzucanie plikow z katalogu rbc do katalogu nowo utworzonego, usuwanie przedrostków przed @"""
    print(f"Presyłanie plików RBC...")
    with conn.open_sftp() as sftp:
        for plik in lista:
            path = f'{sciezka}/{plik}'
            plik_przyciety = plik.split('@')[1]
            remothe_path = f"/home/{tgi}/{katalog_}/{plik_przyciety}"

            sftp.put(path, remothe_path)


def katalog_wybor():
    """Określanie ścieżki i sprawdzanie struktury katalogów"""
    while True:
        sciezka_init = filedialog.askdirectory(title='Wybór katalogu linii dla danego projektu')
        licznik = 0
        lista_stacji = []
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
                    print("W katalogu 00_ctc/.dmt jest więcej niż jeden plik, do poprawy.")
                    licznik += 1
                elif ilosc == 0:
                    print("Brak plików w katalogu 00_ctc/.dmt, do poprawy.")
                    licznik += 1
                elif ilosc == 1:
                    if pliki[0].endswith('.7z'):
                        print("Złe rozszerzenie pliku bazodanowego. Jest 7z, powinno być zip.")

            if sciezka.count(r'\00_ctc\rbc\01\config'):
                if len(pliki) != 8:
                    print("W katalogu rbc/01/config powinno być 8 plików, do poprawy")
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
                    print("Brak katalogów opr")
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
                                print(f"Brak katalogów w {stacja}, do poprawy.")
                            elif len(zwrot) == 2:
                                try:
                                    zwrot = os.listdir(os.path.join(sciezka_init, stacja, 'his_rbc'))
                                    if len(zwrot) != 2:
                                        print(f'Brak katalogów w {stacja}/his_rbc, do poprawy.')
                                        licznik += 1
                                except FileNotFoundError:
                                    print(f"Brak katalogu {stacja}/his_rbc")
                                    licznik += 1

                                try:
                                    zwrot = os.listdir(os.path.join(sciezka_init, stacja, 'im/01/config'))
                                    if len(zwrot) != 1:
                                        print(f'Brak pliku elem.dat w {stacja}/im/01/config, do poprawy.')
                                        licznik += 1
                                except FileNotFoundError:
                                    print(f"Brak katalogu {stacja}/im/01/config")
                                    licznik += 1

                        except FileNotFoundError:
                            print(f"Brak katalogu stacyjnego {stacja}, do poprawy.")
                            licznik += 1



        if licznik > 0:
            input("Są rzeczy do poprawy. Naciśnij coś żeby wyjść i poprawić.")
            sys.exit()

        break



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
    print("Odpalam initProdRepo...")
    channel.send(f"initProdRepo -setview -cae {katalog_init} -src /home/{tgi}/{katalog_init} PKP.1.3.2.0 02\n".encode())
    zwrot = skan_zwrot(channel)
    if zwrot.count('incorrect parameters'):
        input('Coś nie tak z initProdRepo, naciśnij coś żeby zobaczyć loga')
        print(zwrot)
        channel.close()
        rbc_prod_conn_init.close()
        sys.exit()
    print('initProdRepo OK')


def configure_all(rbc_prod_conn_init, channel):
    """Uruchamianie skryptów 'configureAll' i 'collectUserData'"""
    print("Odpalam configureAll...")
    channel.send(f"configureAll customer\n".encode())
    zwrot_configure = skan_zwrot(channel)
    if not zwrot_configure.count('successful.'):
        _ = input("\nCoś nie tak z configureAll, naciśnij coś żeby zobaczyć loga.")
        print(zwrot_configure)
        zamykanie_polaczenia(rbc_prod_conn_init, channel)
        sys.exit()
    print('configureAll OK')

    print('Odpalam collectUsedData...')
    channel.send(f"collectUsedData customer\n".encode())
    _ = skan_zwrot(channel, ciag_znakow='Return only.')  # Nie ma co sprawdzać

    channel.send('cd; ConfigDataRBC2Pdf.sh DataProd.xml\n'.encode())
    zwrot_pdf = skan_zwrot(channel)
    if not zwrot_pdf.count('DataProd.xml transformed to DataProd.pdf'):

        _ = input("\nCoś nie tak z ConfigDataRBC2, naciśnij coś żeby zobaczyć loga.")
        print(zwrot_configure)
        zamykanie_polaczenia(rbc_prod_conn_init, channel)
        sys.exit()

    channel.send('exit\n'.encode())
    skan(channel)
    channel.send('exit\n'.encode())
    skan(channel)


def katalog_roboczy(channel):
    while True:
        katalog = input('Podaj nazwę katalogu roboczego do wrzucenia danych RBC: ')
        if not tworzenie_katalogu_rbc(channel, katalog).count('mkdir: Failed'):
            print(f"Utworzono katalog {katalog}")
            break
        else:
            print(f"Katalog {katalog} już istnieje.")
    return katalog


def tworzenie_katalogu_rbc(channel, katalog_nowy):
    """Tworzenie katalogu w katalogu domowym"""
    channel.send(f"mkdir {katalog_nowy}\n".encode())
    return skan_zwrot(channel)


def create_cd(conn, channel, login, haslo='', debers=''):
    """Tworzenie obrazu createCDs"""
    print("Odpalanie skryptu CreateCDs...")
    channel.send("cd /local/CD_3.3.6/bin\n".encode())
    skan(channel, login, debers)
    channel.send(f"sudo ./createCDs -aur {login} debersuwg-rbcprod1\n".encode())
    zwrot = skan_zwrot(channel, login, debers, 'Press any key to continue ...', haslo)

    if not zwrot.count('was generated'):
        print(zwrot)
        _ = input("Coś poszło nie tak z ")
        zamykanie_polaczenia(conn, channel)

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
            f"clearfsimport -nsetevent -recurse -mklabel {etykieta} /home/{login}/project_data/poland/{linia} .\n".encode())
        skan_zwrot(channel, login, debers)
        return None

def zamykanie_polaczenia(conn, channel):
    """Zamykamy połączenie z hostem"""
    conn.close()
    channel.close()

def etykieta_cc():
    """Określanie etykiety do CC"""
    while True:
        etykieta = input("Podaj etykietę: ")
        potw = input(f"Etykieta to {etykieta}, zgadza się?[T/N]: ").upper()
        if potw == 'T':
            zwrot = etykieta
            break
    return zwrot

def linia_cc(linia, przelacznik = True):
    """Określanie katalogu linii do CC"""
    while True:
        if przelacznik:
            decyzja = input(f"Czy {linia} to katalog linii do importu plików do CC?[T/N]: ").upper()
        else:
            decyzja = 'N'

        if decyzja == 'T':
            zwrot = linia
            break
        elif decyzja == 'N':
            while True:
                linia_zwrot = input("Podaj katalog linii: ")
                potw = input(f"Katalog linii to {linia_zwrot}, zgadza się?[T/N]: ").upper()
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

def weryfikacja_plikow_na_home():
    pass


if __name__ == '__main__':
    rbc_prod = '10.220.30.208'
    debersuxvl03 = '10.220.181.133'
    debersuxv045 = '10.220.30.245'
    debers00008 = '10.220.30.24'
    # debers058 = '10.220.30.98'
    # debers794 = '10.48.71.44'

    lista_plikow_rbc, sciezka_do_katalog_rbc = katalog_wybor()

    """linia_main = sciezka_do_katalog_rbc.split("/")[-5]

    login_main = input('\nPodaj login do produkcji obrazu rbc: ')
    login_abbbr = login_main.split('_')[0]
    haslo_main = getpass.getpass(prompt='Podaj haslo: ')

    debers_08_conn, channel_debers_08 = nawiazanie_polaczenia(debers00008, login_abbbr, haslo_main)

    #weryfikacja_plikow_na_home(channel, login_abbbr, katalog)

    # Przechodzimy do katalogu poland
    channel_debers_08.send('cd /cc/l905/customer/poland\n'.encode())
    skan(channel_debers_08, login_abbbr, 'debers00008')
    
    weryfikacja_plikow_na_home(channel_debers_08, )
    
    
    # Określamy i sprawdzamy etykietę
    etykieta_main = etykieta_cc()

    while True:
        poprawne_etykieta = weryfikacja_etykiety(channel_debers_08, etykieta_main, login_abbbr)
        if poprawne_etykieta:
            break
        else:
            print(f'Etykieta {etykieta_main} istnieje podaj jeszcze raz')
            etykieta_main = etykieta_cc(linia_main, przelacznik=False)

    # Określamy i spr katalog linii
    katalog_linii = linia_cc(linia_main)
    while True:
        poprawne = weryfikacja_linii(channel_debers_08, katalog_linii, login_abbbr)
        if poprawne:
            break
        else:
            print(f'Podany katalog {katalog_linii} istnieje podaj jeszcze raz')
            etykieta_main = linia_cc(linia_main, przelacznik=False)

    # TODO Sprawdzanie czy pliki są w odpwoednich katalogach
    # TODO, jeśli nie są to przesuwamy
    # TODO Wrzucanie SFTP

    # TODO Spr czy są pliki image
    # TODO spr czy sa
    print("Preview importu plików...")
    zwrot_import_preview = import_danych_do_cc(channel_debers_08, 'debers00008', login_abbbr,
                                               katalog_linii, etykieta_main, True)

    # TODO sprawdzanie czy są pliki oznaczone jako new element

    zwrot_import = import_danych_do_cc(channel_debers_08, 'debers00008', login_main.split('_')[0],
                                       katalog_linii, etykieta_main, False)

    # TODO Tworzenie obrazu his rbc
    # TODO import obrazow

    

    # Zaczynamy od połączenia do rbc_prod
    print("Łączenie z hostem do produkcji obrazu RBC...")
    rbc_prod_conn, channel_rbc = nawiazanie_polaczenia(rbc_prod, login_main, haslo_main)
    print(f"Ok, połączono z {rbc_prod}")

    # Tworzymy katalog, jeśli już jest pytamy jeszcze raz
    katalog_rbc = katalog_roboczy(channel_rbc)

    # Import plików rbc
    wrzucanie_plikow(rbc_prod_conn, login_main, lista_plikow_rbc, katalog_rbc, sciezka_do_katalog_rbc)

    # Uruchamiamy skrypt initProdRepo
    init_prod_repo(rbc_prod_conn, channel_rbc, login_main, katalog_rbc)

    # Uruchamiamy skrypty configAll, collect.., pdf
    configure_all(rbc_prod_conn, channel_rbc)

    zamykanie_polaczenia(rbc_prod_conn, channel_rbc)

    print("Łączenie z hostem debersuxvl03...")
    debersuxvl03_conn, debersuxvl03_channel = nawiazanie_polaczenia(debersuxvl03,
                                                                    login_main, haslo_main, debers='debersuxvl03')
    print(f"Ok, połączono z debersuxvl03")

    folder_obraz_rbc = create_cd(debersuxvl03_conn, debersuxvl03_channel, login_main, haslo_main, 'debersuxvl03')
    test_poprawnosci_polecenia(debersuxvl03_channel, login_main, 'debersuxvl03')

    _ = input("Przerwa")

    zamykanie_polaczenia(debersuxvl03_conn, debersuxvl03_channel)

    #Łączenie z debers0008"""
