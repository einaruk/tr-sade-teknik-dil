---
name: tr-sade-teknik-dil
description: Türkçe ya da İngilizce teknik metni, okuyanın yanlış anlayamayacağı sade biçime çevirir ve yapısal kuralları script ile denetler. ASD-STE100 (Simplified Technical English) ilkelerinin iki dilli uyarlamasıdır. Metni insan yardımı olmadan bir ajan, çeviri hattı ya da ana dili farklı bir okur çözecekse kullanılır: tool açıklaması, hata mesajı, ajanlar arası talimat, system prompt, prosedür adımı, durum raporu, proje tanım dokümanı (PTD) ya da teklif maddesi. Yaratıcı ve pazarlama metni için değildir. Tetikleyiciler; "sadeleştir", "sade teknik dil", "STE ile yaz", "STE100 rewrite", "bu metni netleştir", "ajan yanlış anlamasın", "edilgenleri temizle", "cümleleri böl", "metni lint et", "disambiguate", "plain-language rewrite", "apply Simplified Technical English".
metadata:
  version: "0.1.1"
---

# Sade Teknik Dil (ASD-STE100 uyarlaması, Türkçe + İngilizce)

ASD-STE100, havacılık bakım talimatları yanlış okunmasın diye yazılmış bir kontrollü dil
standardıdır. Yanlış okumanın iki kaynağını kapatır: birden çok anlamı olan kelime ve birden çok
biçimde çözülebilen cümle. Bu skill aynı disiplini, metni soru soramadan çözen okura uygular.
Bu okur bir ajan, bir çeviri hattı ya da ana dili farklı bir insandır.

**Türkçe kısmın statüsü.** ASD-STE100 yalnız İngilizceyi tanımlar. Buradaki Türkçe kurallar o
ilkelerin bu skill'e ait uyarlamasıdır. "STE uyumlu Türkçe" diye bir şey yoktur. Çıktıyı öyle
adlandırma. İngilizce kısım `danyuchn/asd-ste100-skill` v0.4.0'dan (MIT) değişmeden gelir.

## Ne zaman

- Metin yoğun, dolaylı, çok yan cümleli ya da belirsiz okunuyor.
- Metni başka bir ajan, çeviri hattı ya da ana dili farklı biri okuyacak ve yanlış okumanın bedeli var.
- Prompt, system message, tool açıklaması, prosedür, hata mesajı yazıyorsun.
- Kullanıcı önce/sonra karşılaştırması istiyor (istemezse yalnız sonuç metni verilir).

Yaratıcı, ikna edici ya da pazarlama metnine uygulama: bu dil bilerek düz ve yalındır.

## İki mod

Yazmadan önce modu seç. Kullanıcı söylemediyse metin türünden çıkar.

- **Sıkı** — prosedür, hata mesajı, tool/fonksiyon açıklaması, ajanlar arası talimat, güvenlik
  metni. Aşağıdaki bütün kurallar, uzunluk sınırı ve "tek iş için tek kelime" dahil.
- **Sade** — README, PR açıklaması, changelog, açıklayıcı düzyazı, proje dokümanı ya da teklif maddesi. Yapısal
  kurallar tam uygulanır. "Tek iş için tek kelime" öneri düzeyinde kalır.

## Kurallar

Kurallar iki türdür. **Yapısal kurallar** cümlenin biçimini anlatır ve tek başına uygulanabilir.
**Sözcük kuralları** bir sözlüğe dayanır. ASD'nin ~900 kelimelik sözlüğü burada yoktur (yeniden
dağıtılamaz). Türkçesi hiç yoktur. Sözcük kurallarını yön olarak uygula, sözlük uyumu iddia etme.

**Tablo 1 (v1.0) — Yapısal kurallar (her iki dil)**

| # | Kural | Türkçe: yap | Türkçe: yapma | English: do / don't |
|---|---|---|---|---|
| 1 | Etken çatı | "Ajan dosyayı siler." | "Dosya (ajan tarafından) silinir." Fail gerçekten bilinmiyor ya da önemsizse edilgen kalabilir. | "The agent deletes the file." / "The file is deleted." |
| 2 | Cümle başına tek iş | "Dosyayı aç. 3. satırı oku." | "Dosyayı açıp 3. satırı okuduktan sonra eşleşiyorsa kaydet." Ulaç zinciri (-ıp, -arak, -dıktan sonra, -ınca, -ken) ve "olup" cümle birleştirir. | "Open the file. Read line 3." / "Open the file and read line 3, then check…" |
| 3 | Cümle uzunluğu | Türkçe: talimatta ≤15, açıklamada ≤18 kelime | Uzun, iç içe yan cümleler | ≤20 words instructions, ≤25 descriptions |
| 4 | Noktalı virgül yok (Kural 8.1) | İki ayrı cümle | Herhangi bir noktalı virgül | Split into separate sentences |
| 5 | Yalın zaman | "Çalışma sürüyor." "Kurulum bitti." | "Çalışma devam etmektedir." "Kurulum tamamlanmış bulunmaktadır." "yapmış olduğu" | "We received the report." / "We have received…" |
| 6 | Fiil, isim değil (Kural 3.7) | "Logu incele." | "Logun incelemesini gerçekleştir." "güncelleme işlemi yapıldı" | "Analyze the log." / "Perform an analysis of the log." |
| 7 | Deyimsel fiil yok (Kural 9.3) | "Servisi başlat." "Logu oku." | "Servisi ayağa kaldır." "Loga göz at." "hayata geçir" | "Start the job." / "Spin up the job." |
| 8 | Kipliği koru | "İstek başarısız olmuş **olabilir**." aynen kalır | Çekinceyi olguya çevirmek ("İstek başarısız oldu.") | "may have failed" stays |
| 9 | Eksiltme yok | Özne, nesne ve fiili açık yaz | Yer kazanmak için kelime düşürmek | Keep subject, verb, article |
| 10 | İsim yığını ≤3 | "yakıt pompası valfi" | 4+ isimli tamlama zinciri | "fuel pump valve" |
| 11 | Paragraf | Tek konu, ≤6 cümle | Çok konulu paragraf | same |
| 12 | Sıra için liste | 3+ adım ya da koşul numaralı/madde işaretli | Sırayı tek cümleye gömmek. Madde bağlaçla ("ve", "veya") bitmez. | same |

**Tablo 2 (v1.0) — Sözcük kuralları (yön olarak)**

| # | Kural | Yap | Yapma |
|---|---|---|---|
| 1 | Tek iş için tek kelime | Bir iş için bir fiil seç, hep onu kullan ("kontrol et") | Aynı işe "kontrol et / doğrula / teyit et", "gönder / ilet / yolla", "sil / kaldır" diye dönmek |
| 2 | Yalın kelime | "bu", "sonra", "hemen", "size", "çünkü", "konusunda" | "işbu", "akabinde / müteakip", "ivedilikle", "tarafınıza", "zira", "hususunda", "istinaden", "arz ederim" |
| 3 | Pazarlama sıfatı yok | İddiayı kanıtlayan ölçümü yaz ya da sıfatı sil | "kusursuz", "çığır açan", "son teknoloji", "yeni nesil", "kendini kanıtlamış" |
| 4 | Alan terimi | Gerekli terimi koru, yaygın değilse bir kez tanımla. Projenin onayladığı terimler sözlüktür ("top kimde"). | Tanımsız jargon |

Türkçe kuralların gerekçesi, sınırları ve ölçülen doğruluk: `references/turkce-kurallar.md`.
İngilizce kuralların kaynağı: `references/writing-rules.md`.

**Zaman kuralının istisnası.** Birleşik biçim bazen yalın biçimin taşıyamadığı bilgiyi taşır:
çekince ya da güncel geçerlilik. O zaman koru ve sapmayı bildir: "olmuş olabilir", "may have failed",
"the job has completed".

## Süreç

1. Modu seç.
2. Metni bir kez anlam için oku: yeniden yazımdan sonra hâlâ ne söylemesi gerektiğini bil.
3. Mekanik ilk geçiş için linter'ı çalıştır: `python scripts/sade-lint.py DOSYA`. Linter dosya
   ya da stdin okur ve dili kendisi algılar. Seçenekler Tablo 3'te.
4. Cümle cümle yürü. Linter'ın her bulgusunu değerlendir. Sonra linter'ın göremediklerini ara:
   - gerçek anlamda kullanılmış deyim (bir tableti masaya yatırmak deyim değildir)
   - listede olmayan ağdalı kelime ve pazarlama sıfatı
   - eş anlamlı isimler ("kullanıcı / müşteri / istemci")
   - isim yığını ve eksiltme

   Linter'ın sözcük kuralları liste tabanlıdır. Listede olmayanı yakalamaz.
5. İşaretlenen her cümleyi anlamı aynen koruyarak yeniden yaz.
   - **Kipliği yazmadan önce kontrol et.** "olabilir", "muhtemelen", "-ebilir", "sanırım" yazarın
     güven düzeyidir ve içeriktir. Çekinceyi olguya çeviren kısa cümle başka bir iddiadır.
   - Kaynağın söylemediği olguyu ekleme: neden, sıklık, mekanizma, fail. Metin faili söylemiyorsa
     fail uydurma. Edilgeni bırak ve bildir.
   - Yeniden yazım gerekli kesinliği (güvenlik koşulu, kapsam sınırı, sayı) düşürecekse uzun
     biçimi koru ve bildir.
6. Çıktıyı ver. Metin zaten uygunsa söyle, zorla değiştirme.

**Tablo 3 (v1.0) — `scripts/sade-lint.py` seçenekleri**

| # | Seçenek | Ne yapar |
|---|---|---|
| 1 | `--lang auto\|tr\|en` | Dil. `auto` (varsayılan) paragraf ve satır bazında algılar. Karışık dokümanda her dil kendi kurallarıyla taranır. |
| 2 | `--json` | Yapılı çıktı (her bulguda `rule`, `level`, `lang`, `line`, `col`, `match`). |
| 3 | `--disable kural1,kural2` | Adı verilen kuralları susturur. |
| 4 | `--allow "terim1,terim2"` | Proje sözlüğü: eşleşmesi bu terimlerden birini içeren bulguyu düşürür. |
| 5 | `--baseline N` | N sert bulguya kadar başarılı sayar (mevcut dokümana alıştırırken). |
| 6 | `--max-words-tr N`, `--max-words-en N` | Cümle uzunluğu sınırı (varsayılan 18 ve 25). |
| 7 | `--selftest` | Kendi kendini sınar. Ayrıntılı test: `python tests/run_tests.py`. |

Kural kimlikleri:
- İki dilde: `semicolon`, `long-sentence`, `nominalization`, `marketing-adjective`,
  `phrasal-verb`, `synonym-rotation`, `dangling-conjunction`, `passive-voice`.
- Yalnız Türkçe: `bureaucratic`, `clause-chain`, `compound-tense`.
- Yalnız İngilizce: `present-perfect`.

`passive-voice`, `compound-tense` ve `present-perfect` öneri düzeyindedir, çıkış kodunu etkilemez.
Linter çekinceyi ve kipliği hiçbir zaman işaretlemez.

## Çıktı biçimi

**Varsayılan: yalnız yeniden yazılmış metin.** Giriş cümlesi, mod duyurusu, ihlal sayısı, değişiklik
özeti, kural tablosu ya da kapanış teklifi ekleme. İzin verilen tek ek `Korundu:` satırıdır.
5. adımda uzun biçimi bilerek koruduysan metnin altına bu satırı yaz. Satır hangi ifadeyi
koruduğunu ve hangi kesinliğin kaybolacağını söyler.

**İstek üzerine: kural tablosu.** Kullanıcı gerekçeyi görmek isterse şu tabloyu ver ("farkı
göster", "hangi kuralı çiğnemiş", "önce/sonra"). Altına bilerek sadeleştirmediğin yeri tek
satırla yaz:

```markdown
**Tablo: Sadeleştirme farkı (Sıkı mod, 3 ihlal)**

| # | Çiğnenen kural | Önce | Sonra |
|---|---|---|---|
| 1 | Birleşik zaman | "Çalışmalar devam etmektedir." | "Çalışmalar sürüyor." |
| 2 | İsimleştirme | "Logların incelemesi gerçekleştirildi." | "Ekip logları inceledi." |
```

## Sınırlar

Yapar:
- Yoğun ya da belirsiz Türkçe/İngilizce metni kısa, tek anlamlı, etken cümlelere çevirir.
- Her olguyu, koşulu, kapsam sınırını ve her çekincenin gücünü korur.
- Kalması gereken alan terimi için tek satırlık sözlük maddesi önerir.

Yapmaz:
- ASD sözlüğünü ezberden yeniden üretmez. Havacılık düzeyinde STE uyumu garanti etmez. Gerçek
  bakım dokümanı için standardı [resmî siteden](https://www.asd-ste100.org/STE_downloads.html) iste.
- Türkçe çıktıyı bir standarda uygun diye sunmaz: Türkçe için böyle bir standart yoktur.
- Güvenlik koşulunu, istisnayı ya da kapsam sınırını kısaltmak için sessizce düşürmez.
- "başarısız olmuş olabilir"i "başarısız oldu"ya çevirmez.
- Zayıf içeriği doğru ya da yararlı yapmaz. Boş paragraf bu kurallarla temiz ve kısa bir boş
  paragraf olur. Metnin söyleyecek şeyi yoksa bunu söyle.
- Açıklığın bozulduğu noktadan öteye kısaltmaz. Amaç kelime atmak değil, belirsizliği kaldırmaktır.

## Ek kaynaklar

- `references/turkce-kurallar.md` — Türkçe uyarlama kararları, kuralların tanıma yöntemi, bilinen
  kör noktalar ve ölçülen doğruluk.
- `references/writing-rules.md` — ASD-STE100 kural kategorilerinin özeti ve kaynakları (İngilizce).
- `examples/once-sonra-tr.md` — Türkçe önce/sonra örnekleri.
- `examples/before-after.md` — İngilizce örnekler (upstream).
- `scripts/sade-lint.py` — iki dilli, yalnız standart kütüphane kullanan linter.
- `tests/cases.json` — regresyon seti, hepsi geçmeli.
- `tests/heldout.json` — linter'ı görmeden yazılmış ölçüm seti.
- `tests/run_tests.py` — koşucu. `--parity` İngilizce bulguları upstream ile karşılaştırır.
