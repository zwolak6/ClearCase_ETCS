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


def skan_zwrot(channel, tgi='', debers='debers00008', ciag_znakow='', haslo=''):
    """Skan i zwrot z terminala. Liczniki są po to, żeby nie wysyłać po kilka razy komend"""
    licznik = 0
    string = ''
    licznik_passwd = 0
    while True:
        y = channel.recv(9999).decode('utf-8')
        string = string + y
        if string.count('{}@{}'.format(tgi, debers)) or string.count('bash-2.03$'):
            break
        if ciag_znakow != '':
            if string.count(ciag_znakow) and licznik == 0:
                time.sleep(0.1)
                channel.send('\n'.encode())
                licznik += 1
        if haslo != '':
            if string.count("rbcprod1's password:") == 1 and licznik_passwd == 0:
                time.sleep(0.1)
                channel.send(f'{haslo}\n')
                licznik_passwd += 1
            elif string.count("rbcprod1's password:") == 2 and licznik == 1:
                time.sleep(0.1)
                channel.send(f'{haslo}\n')
                licznik_passwd += 1
        time.sleep(0.05)
    print(string)
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
    """Ścieżka do plików rbc"""
    while True:
        sciezka = filedialog.askdirectory(title='Wybór katalogu rbc/config')
        if not sciezka:
            sys.exit()
        lista = os.listdir(sciezka)
        if sciezka.count('rbc/01/config'):
            break
        else:
            input('Wybrany katalog nie zawiera ścieżki /rbc/01/config. Naciśnij coś żeby wybrać jeszcze raz')

    return lista, sciezka


def sprawdzanie_zawartosci_rbc(lista):
    """Spr. czy mamy wszystkie pliki"""
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
        channel_rbc.close()
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
        zamykanie_polaczenia(rbc_prod_conn, channel_rbc)
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

    lista_zwrot = zwrot.split('\n')[-10:-1]
    print(lista_zwrot)


def zamykanie_polaczenia(conn, channel):
    """Zamykamy połączenie z hostem"""
    conn.close()
    channel.close()


if __name__ == '__main__':
    rbc_prod = '10.220.30.208'
    debersuxvl03 = '10.220.181.133'
    # debers051 = '10.220.30.91'
    # debers058 = '10.220.30.98'
    # debers794 = '10.48.71.44'

    lista_plikow_rbc, sciezka_do_katalog_rbc = katalog_wybor()

    if not sprawdzanie_zawartosci_rbc(lista_plikow_rbc):
        _ = input('Brakuję plików w katalogu rbc/config albo został wybrany zły katalog')
        sys.exit()

    login_main = input('\nPodaj login: ')
    haslo_main = getpass.getpass(prompt='Podaj haslo: ')

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

    create_cd(debersuxvl03_conn, debersuxvl03_channel, login_main, haslo_main, 'debersuxvl03')
