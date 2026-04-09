# ✨ Třídní Nástěnka & Arkáda

Tohle je moderní webová nástěnka pro třídu, která neslouží jen k psaní obyčejných vzkazů. Je napojená na umělou inteligenci a obsahuje spoustu interaktivních miniher!

## 🎮 Co všechno nástěnka umí?
* **Obyčejné vzkazy:** Psaní textu a nahrávání obrázků.
* **AI Poradna:** Napiš do vzkazu nebo komentáře zavináč (`@AI něco...`) a školní robot ti odpoví.
* **1v1 Duel:** Vyzvi někoho na Kámen, Nůžky, Papír.
* **Kostky:** Hoď si a zjisti, kdo má větší štěstí.
* **Hádej číslo:** Robot si myslí číslo (1-100) a lidi do komentářů hádají. Robot jim radí.
* **Zneškodni bombu:** Vystavíš bombu se 4 drátky a někdo musí tipnout ten správný!

## 🚀 Jak to spustit (Nasazení na server)

Tento projekt je postaven na technologii **Docker Compose** a je plně připraven na školní servery (jako je Kuřim AI Dashboard).

1. Ujistěte se, že máte v repozitáři tyto 3 soubory:
   * `app.py` (samotná aplikace)
   * `Dockerfile` (instrukce pro Python)
   * `compose.yml` (nastavení pro spojení s MongoDB databází)
2. Školní server si sám načte API klíče a propojí aplikaci s databází, stačí na Dashboardu kliknout na "Nasazovat".

## 👑 Jak se stát Administrátorem
Aplikace má systém účtů. Aby ses stal Adminem, nemusíš nikam do kódu psát tajné heslo. Funguje tu pravidlo **"Kdo dřív přijde, ten je šéf"**:

1. Zapni nástěnku.
2. V kolonce Registrace napiš jméno přesně: **`admin`**
3. Zvol si libovolné heslo a zaregistruj se.
4. Gratulujeme! Máš admin práva (můžeš mazat jakýkoliv vzkaz a připínat vzkazy nahoru). Nikdo jiný už se jako admin zaregistrovat nemůže.

## 🕵️‍♂️ Přístup do tajné databáze (Pro Admina)
Zajímá tě, jaká hesla mají tvoji spolužáci, jaká je historie všech odpovědí, nebo chceš podvádět a zjistit si tajné číslo dřív, než ho uhodne někdo jiný? 😉

1. Přihlas se do nástěnky jako účet `admin`.
2. Do adresního řádku prohlížeče připiš za URL adresu **`/admin-db`**
   *(Například: `https://tvuj-projekt.kurim.ithope.eu/admin-db`)*
3. Dej Enter a otevře se ti přehledná tabulka s kompletním obsahem MongoDB databáze v reálném čase.
