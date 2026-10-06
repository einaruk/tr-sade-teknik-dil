# tr-sade-teknik-dil — Türkçe için Sade Teknik Dil

Türkçe teknik metni, okuyanın yanlış anlayamayacağı sade biçime çeviren bir agent skill'i ve
linter. Claude Code ile ve `SKILL.md` okuyan diğer ajanlarla çalışır.

**Esin kaynağı.** Bu proje
[danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) yapısından esinlenir ve
ondan türetilmiştir (v0.4.0, MIT). O skill,
[ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/) kurallarını İngilizce metne
uygular. ASD-STE100 yalnız İngilizceyi tanımlar. Bu proje aynı ilkeleri Türkçeye uyarlar.
İngilizce kuralları da değiştirmeden taşır. Karışık dilli dokümanda her dil kendi kurallarıyla
taranır.

> Türkçe kısım bir uyarlamadır, standart değildir. "STE uyumlu Türkçe" diye bir şey yoktur.

## Neden

STE, uçak bakım talimatı yanlış okunmasın diye yazıldı. Okur çoğu zaman ana dili İngilizce olmayan
bir teknisyendi ve yazara soru soramıyordu. Standardın çözümü şudur: kelime başına tek anlam, etken
çatı, yalın zaman, cümle başına tek iş, kısa cümle.

Başka bir ajanın çıktısını okuyan ajan aynı durumdadır. "Şunu mu demek istedin?" diye soramaz.
Türkçe teknik yazının bazı alışkanlıkları bu okuru zorlar: "-mektedir", "olup", "tarafından", ulaç
zinciri, "işbu", "hayata geçir". Bu skill o alışkanlıkları bulur ve metni anlamı bozmadan
yeniden yazar.

## Önce / Sonra

**Tablo 1 (v1.0) — Önce / sonra örnekleri (3 örnek)**

| # | Tür | Önce | Sonra |
|---|---|---|---|
| 1 | Tool açıklaması | "Bu araç, verilen klasördeki log dosyalarının taranması işlemini gerçekleştirecek olup, 30 günden eski olduğu tespit edilen dosyalar arşiv ayarının açık olması hâlinde arşive taşınır, aksi hâlde silinir; başka bir sürecin açık tuttuğu dosyalar ise atlanabilir." | "Araç, verilen klasördeki log dosyalarını tarar. Arşiv ayarı açıksa 30 günden eski dosyaları arşive taşır. Arşiv ayarı kapalıysa bu dosyaları siler. Başka bir sürecin açık tuttuğu dosyayı atlayabilir." |
| 2 | Hata mesajı | "Ödeme işleminin gerçekleştirilmesi sırasında banka tarafından yanıt verilmemiş olması nedeniyle işleminiz tamamlanamamış olabilir; kartınızdan tutar çekilmiş olma ihtimali de bulunduğundan tekrar denemeden önce hesap hareketlerinizin kontrol edilmesi önerilmektedir." | "Banka yanıt vermedi. Bu yüzden ödemeniz tamamlanmamış olabilir. Kartınızdan tutar çekilmiş olabilir. Tekrar denemeden önce hesap hareketlerinizi kontrol etmenizi öneririz." |
| 3 | Ajanlar arası talimat | "İnceleme ajanı, kendisine iletilen değişiklik isteğindeki dosyaları okuyarak test kapsamının yeterli olup olmadığını değerlendirdikten sonra bulgularını özet ajanına aktarmalı olup, 500 satırı aşan değişikliklerde bazı dosyaların atlanmış olabileceği de bulgu listesinde belirtilmelidir." | "Sana iletilen değişiklik isteğindeki dosyaları oku. Test kapsamının yeterli olup olmadığını değerlendir. Bulguları özet ajanına ilet. Değişiklik 500 satırı aşıyorsa bulgu listesine şunu yaz: bazı dosyalar atlanmış olabilir." |

İkinci örnekte "olabilir" iki kez kalır. Sistem ödemenin sonucunu bilmiyor. "Ödemeniz
tamamlanmadı" daha kısadır ama başka bir iddiadır. Bu skill çekinceyi olguya çevirmez.

Örnekler bu proje için yazıldı. Upstream örneklerinin çevirisi değildir. Gerekçeleriyle birlikte
altı örnek: [`examples/once-sonra-tr.md`](examples/once-sonra-tr.md). İngilizce örnekler:
[`examples/before-after.md`](examples/before-after.md).

## Linter ne söyler

Girdi (`ornek.md`):

```text
Yedekleme işleminin gerçekleştirilmesi sırasında disk dolmuş olabilir; bu durumda loglara göz atıp eski dosyaları sildikten sonra servisi ayağa kaldırın.
```

Komut ve çıktı:

```text
$ python scripts/sade-lint.py ornek.md
ornek.md:1:1 nominalization: İsimleştirme + boş fiil. Tek fiil kullan (inceleme gerçekleştirildi → incelendi). [yedekleme işleminin gerçekleştirilmesi]
ornek.md:1:1 long-sentence: Cümle 19 kelime (sınır 18). Böl. [19 words]
ornek.md:1:21 passive-voice: Edilgen olabilir. İşi yapanı özne yap, etken fiil kullan (fail bilinmiyor ya da önemsizse kalabilir). [gerçekleştirilmesi]
ornek.md:1:70 semicolon: Noktalı virgül kullanma (STE Kural 8.1). İki ayrı cümle yaz. [;]
ornek.md:1:91 phrasal-verb: Deyimsel fiil. Tek, yalın fiil kullan (ayağa kaldır → başlat, göz at → oku). [göz atıp]
ornek.md:1:95 clause-chain: Tek cümlede 2 ulaç var. Her işi ayrı cümle yap. [atıp, sildikten sonra]
ornek.md:1:139 phrasal-verb: Deyimsel fiil. Tek, yalın fiil kullan (ayağa kaldır → başlat, göz at → oku). [ayağa kaldırın]

7 violations (6 hard, baseline 0), 19 words, 36.8 per 100 words
Hedges/modality (may, might, could, -ebilir, olabilir) are never flagged: confidence is content.
```

"dolmuş olabilir" işaretlenmedi. Çekince içeriktir, linter ona dokunmaz.

## Skill ne yapar

1. Modu seçer. **Sıkı** mod prosedür, hata mesajı, tool açıklaması ve ajanlar arası talimat
   içindir. **Sade** mod README, PR açıklaması ve açıklayıcı düzyazı içindir.
2. Metni anlam için okur.
3. Linter'ı çalıştırır. Linter yapısal kuralları mekanik olarak bulur.
4. Cümle cümle yürür. Linter'ın göremediğini kendisi arar: listede olmayan deyim, eş anlamlı
   isimler, isim yığını, eksiltme.
5. İşaretlenen cümleyi yeniden yazar. Hiçbir olguyu, koşulu, kapsam sınırını ya da çekinceyi
   düşürmez. Kısa biçim kesinliği bozacaksa uzun biçimi korur ve bunu bildirir.
6. Yalnız yeniden yazılmış metni verir. Bilerek sadeleştirmediği yer varsa altına tek satırlık
   `Korundu:` notu ekler.

Gerekçeyi görmek için "farkı göster" ya da "hangi kuralı çiğnemiş" de. Skill o zaman her kuralı
adıyla gösteren bir önce / sonra tablosu verir.

## Kurallar

**Tablo 2 (v1.0) — Linter kuralları (12 kural)**

| # | Kural kimliği | Dil | Düzey | Yakaladığı örnek |
|---|---|---|---|---|
| 1 | `semicolon` | TR + EN | sert | Düzyazıdaki her noktalı virgül. Kod bloğu atlanır. |
| 2 | `long-sentence` | TR + EN | sert | Türkçede 18, İngilizcede 25 kelimeyi aşan cümle. |
| 3 | `passive-voice` | TR + EN | öneri | "Rapor gönderildi." "Rapor ekip tarafından hazırlandı." |
| 4 | `compound-tense` | TR | öneri | "devam etmektedir", "tamamlanmış bulunmaktadır", "yapmış olduğu" |
| 5 | `nominalization` | TR + EN | sert | "Logun incelemesi gerçekleştirildi." "güncelleme işlemi yapıldı" |
| 6 | `phrasal-verb` | TR + EN | sert | "ayağa kaldır", "göz at", "hayata geçir" |
| 7 | `bureaucratic` | TR | sert | "işbu", "tarafınıza", "akabinde", "istinaden" |
| 8 | `marketing-adjective` | TR + EN | sert | "kusursuz", "çığır açan", "son teknoloji" |
| 9 | `clause-chain` | TR | sert | "olup". Tek cümlede iki ya da daha çok ulaç ("indirip açtıktan sonra"). |
| 10 | `synonym-rotation` | TR + EN | sert | Aynı iş için "kontrol et", "doğrula", "teyit et". |
| 11 | `dangling-conjunction` | TR + EN | sert | "ve" ya da "veya" ile biten liste maddesi. |
| 12 | `present-perfect` | EN | öneri | "The job has completed." |

Öneri düzeyindeki kurallar çıkış kodunu etkilemez. Linter çekinceyi ve kipliği hiçbir zaman
işaretlemez: "olabilir", "-ebilir", "muhtemelen", "may", "might".

Kuralların tamamı: [`SKILL.md`](SKILL.md). Her kuralın tanıma yöntemi ve kör noktası:
[`references/turkce-kurallar.md`](references/turkce-kurallar.md).

## Ne kadar doğru

Linter bir çözümleyici değildir. Düzenli ifadeler, ek kalıpları ve kelime listeleriyle çalışır.

**Tablo 3 (v1.0) — Ölçümler (2026-10-06)**

| # | Ölçüm | Kapsam | Sonuç |
|---|---|---|---|
| 1 | Regresyon seti (`tests/cases.json`) | 67 vaka, 81 etiket | 81 / 81 |
| 2 | Kör set, ayarsız ilk koşu (`tests/heldout.json`) | 224 vaka | Beklenen 137 bulgunun 130'u. 520 yasak etiketten 2 yanlış alarm. |
| 3 | Kör set, düzeltmelerden sonra | Aynı 224 vaka | 136 / 137. 2 / 520 yanlış alarm. |
| 4 | İngilizce birebirlik | Upstream'in 5 dosyası, 130 bulgu | Hepsi upstream linter'ı ile aynı. |
| 5 | Gerçek metin, örneklem etiketleme | 6 doküman, 9.961 kelime, 76 etiketli bulgu | 76 bulgunun 67'si doğru. |
| 6 | Gerçek metin, kaçan sayımı | 78 satırlık bir şablon metni | Liste tabanlı kurallar 7 sorunun 2'sini yakaladı. |

Bu sayıları şu çekincelerle oku:

- Linter'ı ve kör seti aynı model ailesi (Claude) yazdı. Kelime dağarcıkları örtüşür. Bu yüzden
  2. ve 3. satır iyimserdir.
- Gerçek metin etiketlerini de model koydu, bir insan değil.
- 18 kelime sınırı sezgisel bir seçimdir. Paralel bir derlemle doğrulanmadı.

Ne beklenmeli:

- **Yapısal kurallar güvenilirdir.** Noktalı virgül, cümle uzunluğu, "olup", ulaç zinciri, birleşik
  zaman.
- **Edilgen kuralı doğru ama gürültülüdür.** Türkçe prosedür dili edilgeni çok kullanır. 100
  kelimede 3–5 bulgu olağandır. Kural bu yüzden öneri düzeyindedir.
- **Liste tabanlı kurallar isabetli ama eksiktir.** Deyim, ağdalı kelime, pazarlama sıfatı:
  işaretlediği genellikle doğrudur, listede olmayanı görmez.
- **Anlam gerektiren iş linter'da yoktur.** Gerçek anlam ile deyim ayrımı ("tableti masaya yatır"),
  faili bilinmeyen edilgen, eş anlamlı isimler. Bunlar skill'i uygulayan modelin işidir.

Sıfır bulgu, metnin anlamının korunduğunu kanıtlamaz. Linter yalnız biçime bakar.

Bu README linter'dan temiz geçmez: tablolar yasak kalıpları alıntılar. Bulguları kusur diye
değil, örnek diye oku.

## Kurulum

Gereken: Python 3.9 ya da üstü. Linter yalnız standart kütüphaneyi kullanır.

Skill'i Claude Code'un kişisel skill klasörüne klonla:

```bash
git clone https://github.com/einaruk/tr-sade-teknik-dil ~/.claude/skills/tr-sade-teknik-dil
```

Skill bundan sonra her Claude Code projesinde görünür. Güncellemek için klasörde `git pull`
çalıştır.

## Kullanım

Skill'i bir sadeleştirme isteğiyle tetikle:

```text
Bu tool açıklamasını sadeleştir
Bu hata mesajını ajan yanlış anlamasın diye yeniden yaz
Bu metni lint et
```

Linter'ı tek başına da kullanabilirsin:

```bash
python scripts/sade-lint.py DOSYA.md                 # dili kendisi algılar
python scripts/sade-lint.py --lang tr --json DOSYA.md
python scripts/sade-lint.py --allow "top kimde,dürt" DOSYA.md   # proje sözlüğü
python scripts/sade-lint.py --baseline 12 DOSYA.md   # 12 sert bulguya kadar başarılı say
cat DOSYA.md | python scripts/sade-lint.py                 # stdin
```

Sert bulgu varsa çıkış kodu 1 olur. Seçeneklerin tamamı `SKILL.md` içindeki Tablo 3'tedir.

## Testler

```bash
python scripts/sade-lint.py --selftest
python tests/run_tests.py                                   # regresyon: hepsi geçmeli
python tests/run_tests.py --measure tests/heldout.json --failures
```

- `tests/cases.json`: 67 regresyon vakası. Her vaka bir metin, beklenen kurallar ve yasak
  kurallardır. Hepsi geçmelidir.
- `tests/heldout.json`: 224 vakalık ölçüm seti. Linter'ın kodunu görmeyen ayrı bir ajan yazdı.
  Bu set bir geçme şartı değildir, isabeti ölçer.
- `tests/run_tests.py --parity UPSTREAM.py DOSYA...`: İngilizce bulguları upstream linter'ı ile
  karşılaştırır.

## Kapsam

Uygun: ajanlar arası mesaj, tool ve fonksiyon açıklaması, hata mesajı, system prompt. Prosedür
adımı, durum raporu, teklif ve proje dokümanı maddesi de uygundur.

Uygun değil: yaratıcı metin, pazarlama metni, üslubun önemli olduğu her yazı. Bu dil bilerek düz
ve yalındır.

Bir sınır daha: skill metnin biçimini düzeltir, içeriğini düzeltmez. Söyleyecek şeyi olmayan
paragraf kısa, temiz ve yine boş çıkar.

ASD'nin yaklaşık 900 kelimelik onaylı sözlüğü burada yoktur. Sözlük yeniden dağıtılamaz ve
Türkçesi hiç yoktur. Sertifikalı STE dokümanı için
[gerçek standardı](https://www.asd-ste100.org/STE_downloads.html) kullan.

## Katkı

Liste tabanlı kurallar gerçek metinle büyür. Kaçan bir kalıp ya da yanlış alarm gördüysen:

1. Kalıbı `scripts/sade-lint.py` içindeki ilgili listeye ekle ya da listeden çıkar.
2. `tests/cases.json` içine bir "yakalamalı" ve bir "yakalamamalı" vaka ekle.
3. `--selftest` ve `tests/run_tests.py` çalıştır. İkisi de temiz geçmeli.
4. `--measure tests/heldout.json` sonucunun kötüleşmediğini kontrol et.

Ayrıntı: [`references/turkce-kurallar.md`](references/turkce-kurallar.md), "Listeyi büyütme".

## Kaynaklar

- [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill): bu projenin
  türetildiği skill
- [ASD-STE100 resmî sitesi](https://www.asd-ste100.org/)
- [Simplified Technical English — Wikipedia](https://en.wikipedia.org/wiki/Simplified_Technical_English)
- [`references/writing-rules.md`](references/writing-rules.md): ASD-STE100 kural kategorilerinin
  özeti (İngilizce, upstream)

## Lisans

MIT. [LICENSE](LICENSE) dosyası upstream telif satırını korur.
