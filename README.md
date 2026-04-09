# 📌 Třídní Nástěnka s AI

Ahoj! Tohle je jednoduchá aplikace, která funguje jako digitální nástěnka. Můžeš na ni psát vzkazy, nahrávat obrázky a dokonce si povídat s umělou inteligencí. 

Tady je jednoduchý návod, jak si ji zapnout u sebe na počítači (zvládne to každý, slibuju!).

## Krok 1: Příprava (Co musíš mít v počítači)
Abys mohl aplikaci spustit, potřebuješ programovací jazyk Python. 
1. Jdi na stránku [python.org/downloads](https://www.python.org/downloads/) a stáhni si nejnovější verzi.
2. **DŮLEŽITÉ:** Při instalaci hned na první obrazovce **zaškrtni políčko „Add Python to PATH“** (Přidat Python do cesty). Pak instalaci normálně doklikej.

## Krok 2: Stažení Nástěnky
1. Na této stránce nahoře klikni na zelené tlačítko **Code** a vyber **Download ZIP**.
2. Stažený ZIP soubor si rozbal někam do počítače (třeba na Plochu do složky `Nastenka`).

## Krok 3: Získání "Klíče" pro AI
Aplikace potřebuje tajný klíč, aby se mohla spojit s umělou inteligencí.
1. Otevři složku s rozbalenou nástěnkou.
2. Vytvoř tam úplně obyčejný textový dokument (pravé tlačítko -> Nový -> Textový dokument).
3. Pojmenuj ho přesně **`.env`** (nezapomeň na tu tečku na začátku a smaž koncovku .txt).
4. Otevři tento soubor (třeba v Poznámkovém bloku) a vlož do něj toto:

```text
OPENAI_API_KEY=sem_vlozis_svuj_tajny_klic
OPENAI_BASE_URL=[https://kurim.ithope.eu/v1](https://kurim.ithope.eu/v1)
PORT=5000
```
*(Místo `sem_vlozis_svuj_tajny_klic` dej svůj opravdový klíč, který jsi dostal).*

## Krok 4: Jdeme to zapnout!
1. Otevři složku s nástěnkou.
2. Nahoře do řádku s adresou (tam, kde je napsáno např. `C:\Users\Plocha\Nastenka`) klikni, smaž to, napiš tam **`cmd`** a zmáčkni Enter. Otevře se ti černé okno.
3. Do černého okna napiš tento příkaz a dej Enter (tím se stáhnou potřebné součástky):
   ```bash
   pip install -r requirements.txt
   ```
4. Až to doběhne, napiš poslední příkaz a dej Enter:
   ```bash
   python app.py
   ```
5. **Hotovo!** Aplikace teď běží. Otevři svůj internetový prohlížeč (Chrome, Edge...) a do adresního řádku napiš: **`http://localhost:5000`**

*Poznámka: Až budeš chtít nástěnku vypnout, stačí křížkem zavřít to černé okno.*
