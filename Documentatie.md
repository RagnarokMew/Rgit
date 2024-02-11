# Proiect Atesta

Realizat de Simion Stefan

## Rgit

## Cuprins

#### 1 Introducere - pg

#### 2 Consideratii Teoretice - pg

###### 2.1 Ce este un sistem de control? - pg

###### 2.2 Cum functioneaza Rgit (Git)? - pg

###### 2.3 Initializarea unui repository - pg

###### 2.4 Crearea unei intrari (entry) in index - pg

###### 2.5 Crearea unui commit -pg

###### 2.6 Checkout (verificarea) unui commit -pg

###### 2.7 Crearea unei ramuri (branch) - pg

#### 3 Prezentare Proiect - pg

#### 4 Bibliografie - pg

## 1 Introducere

&nbsp;&nbsp;&nbsp;&nbsp;Proiectul a fost realizat in limbajul de programare python. Am utilizat Python 3, deoarece are o sintaxa simpla usoara de inteles si de citit si are o biblioteca standard larga ce usureaza dezvoltarea aplicatiilor.

&nbsp;&nbsp;&nbsp;&nbsp;Python este un limbaj de programare high-level (de nivel inalt), pentru uz general. In acest limbaj de programare, accentul este pus pe lizibilitatea codului prin utilizarea unei indentatii semnificative. Python a inceput in anii 1980 ca un succesor al limbajului de programare ABC si a fost publicat pentru prima oara in anul 1991 drept Python 0.9.0. Python 2.0 a fost lansat in anul 2000, iar Python 3.0 (versiunea de python utilizata in acest proiect) a fost lansata in 2008, care a fost o revizie majora a limbajului de programare si nu este compatibila cu versiunile trecute.

&nbsp;&nbsp;&nbsp;&nbsp;Python poate fi utilizat pentru aproape orice scop dar acest limbaj de programare este utilizat pentru niste activitati precum: dezvoltare web si software, automatizarea unor activitati (task automation), machine learning, AI (inteligenta artificiala) si in stiinta datelor (data science). In dezvoltarea web si software se remarca Django, cel mai utilizat framework de python, realizat pentru a accelera timpul de constructie al aplicatiei (app build time). Pentru automatizarea unor activitati, se utilizeaza fie module incorporate, fie cod pre-scris (pre-written) din biblioteca standard python. Python este cel mai preferat limbaj pentru machine learning, AI si stiinta datelor (data science), avand necesare pentru acestea si multe biblioteci precum NumPy, Pandas si Matplotlib, pentru automatizarea unor functii precum curatarea, transformarea si vizualizarea datelor.

&nbsp;&nbsp;&nbsp;&nbsp;Rgit, proiectul de atestat put in discutie, este o implementare partiala a unui sistem de control al versiunilor (version control system), implementat in python, avand o functionalitate primitiva a Git. In cadrul acestui document, "implementarea primitiva" a proiectului de atestat este doar o comparatie cu alte sisteme de version control (in acest caz fiind Git), avand cele mai importante si mai utilizate comenzi de version control si niste masuri de protectie impotriva stergerii si suprascrierii (overwriting) fisierelor in mod neintentionat (oprirea instructiunilor) (Alte sisteme de control al versiunilor, precum Git au masuri de protectie mult prea complexe pentru a fi implementate).

&nbsp;&nbsp;&nbsp;&nbsp;Rgit a fost creat specific pentru a rula in sisteme asemanatoare Unix care au un interpret Python (python interpreter) (spre exemplu: Ubuntu) si este posibil sa nu ruleze pe Windows sau sa aiba un comportament nedefinit. Testarea necesita neaparat un shell compatibil cu bash (bash-compatible shell). WSL (Windows Subsystem for Linux) nu a fost testat cu Rgit, dar ar trebui sa functioneze. Rgit a fost creat pentru utilizarea in CLI (Command Line Interface) si necesita neaparat utilizarea unui terminal pentru a functiona (exemplu de CLI: Terminal - Linux / macOS; Command Prompt - Windows).

&nbsp;&nbsp;&nbsp;&nbsp;Rgit implementeaza 15 comenzi de version control (din cele 135 comenzi si subcomenzi ale Git):

* add
* cat-file
* check-ignore
* checkout
* commit
* hash-object
* init
* log
* ls-files
* ls-tree
* rev-parse
* rm
* show-ref
* status
* tag

## 2 Consideratii Teoretice

#### 2.1 Ce este un sistem de control?

&nbsp;&nbsp;&nbsp;&nbsp;Un sistem de control al versiunii este un instrument (tool) care ajuta in urmarirea (si gestionarea) modificarilor aduse fisierelor de-a lungul timpului dezvoltarii unui proiect. Pe scurt (si simplificat), un sistem de control al versiunii este un istoric al tuturor fisierelor unui proiect.

#### 2.2 Cum functioneaza Rgit (Git)?

&nbsp;&nbsp;&nbsp;&nbsp;In cadrul prezentarii teoretice termenii ```rgit``` si ```git``` sunt interschimbabili, fiind utilizate comenzi comune celor doua siteme de control al versiunii. Alti termeni ce vor fi utilizati interschimbabili sunt: ```repo``` si ```repository```. Prezentarea teoretica va urmari rularea ipotetica si simplificata a rgit/git de la inceputul crearii unui proiect, cu scopul de a forma o imagine asupra functionalitatii programului. Demonstratia teoretica nu reprezinta rularea actuala a rgit/git si valorile afisate sunt alese arbitrar si nu reprezinta instructiuni pentru rularea programului rgit (fiid omise detalii esentiale). Pentru rularea actuala si pasii pentru a rula rgit sa se verifice ```3 Prezentare Proiect```. Pentru prezentarea teoretica sunt necesare niste cunostinte rudimentare despre terminal (si bash) precum (comenzile nu sunt prezentate integral ci doar functionalitatea utilizata in prezentarea teoretica):

* ```cd```
  Comanda ```cd <target>``` schimba directorul (folderul) actual in cel din ```<target>```, o cale (path) relativ (fata de directorul (folderul) deschis actual) sau absoluta (fata de directorul (folderul) root)

* ```mkdir```
  Comanda ```mkdir <target>``` creeaza un directorul (folderul) din ```<target>```, o cale (path) relativa sau absoluta la un director (folder) care nu exista inca. Exemple:
  ```mkdir folder1``` va crea un director (folder) numit ```folder1``` in directorul (folderul) actual;
  ```mkdir folder1/folder2``` va crea un director (folder) numit ```folder2``` in directorul (folderul) ```folder1``` din directorul (folderul) actual (daca ```folder1``` nu exista atunci comanda va intoarce o eroare)
  ```mkdir ~/folder_in_root``` va crea un director (folder) numit ```folder_in_root``` in root (```~```);
  
* ```cat```
  Comanda ```cat <target>``` va afisa continutul ```<target>```, o cale (path) relativa sau absoluta la un fisier
  Spre exemplu, rularea comenzii ```cat ~/main.c```, ```main.c``` fiind un fisier sursa C ar putea avea urmatorele date de iesire (output):

  ```
  #include<stdio.h>
  #include<stdlib.h>
  #include<string.h>

  #define STR_MAX 256

  int main(void)
  {
    char* text = malloc(STR_MAX);
    memcpy(text, "Hello World!", strlen("Hello World")+1);
    fprintf("stdin","%s",text);
    free(text);
    return 0;
  }
  ```
  
* ```printf```
  Comanda ```printf <text>``` este similara cu functia ```printf()``` din C si ```echo```, putant formata rezultatul afisat (output). Spre exemplu:
  ```printf "I am a piece of text"``` afiseaza ```I am a piece of text```

#### 2.3 Initializarea unui repository

Vom crea directorul (folderul) in care vom avea proiectul si unde se va desfasura prezentarea teoretica si vom intra in acesta:

```
$ mkdir project
$ cd project
```
Apoi vom crea un director (folder) numit ```data``` in care vom care vom crea un fisier ```letter.txt``` si vom pune in acesta caracterul 'a':

```
$ mkdir data
$ printf 'a' > data/letter.txt
```

Acum structura proiectului ar trebui sa arate precum:

\<FirstGraphGoesHere\>

Apoi vom initializa repository-ul si vom adauga fisierul ```letter.txt``` intr-un commit (in staging area; staging area este faza precedenta realizarii unui commit)

```
$ git init
$ git add data/letter.txt
```

Dupa rularea comenzilor de mai sus se vor genera urmatoarele schimbari in directorul (folderul) proiectului:

\<SecondGraphGoesHere\>

Fiecare obiect creat in git are un hash prin care poate fi identificat, fiecare obiect avand un hash unic. Hash-ul unui obiect are de obicei 40 de caractere, dar pentrul scopul prezentarii acesta va fi restrans la 4 caractere.
Primele 2 caractere al unui hash reprezinta devin numele directorului in care se afla fisierul ce are continutul fisierului original (in acest caz ```letter.txt```), iar restul devin numele fisierului respectiv dupa cum se poate observa:

```
$ git hash-object data/letter.txt
2e65
$ cat .git/objects/2e/65
XK??OR0dH
```

Dupa cum se poate observa continutul fisierului asociat ```letter.txt``` este codificat (encoded). Pentru a vizualiza continutul decodificat al fisierului vom rula comanda ```cat-file```

```
$ git cat-file 2e65
a
```

Astfel vedem continutul decodificat al fiserului ```2e65```, fiind continutul fisierului ```letter.txt```

#### 2.4 Crearea unei intrari (entry) in index

Dupa ce am initializat un repository si am adaugat continutul pe care dorim sa "il salvam", mai exact sa creeam un commit. Inainte de a realiza un commit fisierele trebuie adaugate in index (o lista de fisiere urmarite de git).

```
cat ./git/index
?H?u.data/letter.txtd
```

Din datele de iesire (outputul) comenzii de mai sus putem observa ca intreg continutul al fisierului ```index``` este codificat (encoded) si este citit cu greu. Pentru a vizualiza continutul intr-un mod lizibil vom utiliza comanda ```ls-files```.

```
$ git ls-files
data/letter.txt 2e65
```

Din comanda ```ls-files``` putem observa ca datele de iesire (outputul) au un anumit format