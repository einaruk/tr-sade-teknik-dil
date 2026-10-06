# Türkçe Kurallar — Uyarlama Kararları, Tanıma Yöntemi, Ölçülen Doğruluk

ASD-STE100 yalnız İngilizceyi tanımlar. Bu dosya, aynı ilkelerin Türkçeye nasıl taşındığını ve
`scripts/sade-lint.py` linter'ının her kuralı nasıl tanıdığını anlatır. Buradaki eşikler ve kelime
listeleri bu skill'in kendi seçimidir. Yayımlanmış bir Türkçe standarttan gelmez.

## Uyarlama kararları

**Tablo 1 (v1.0) — STE ilkesinin Türkçe karşılığı**

| # | STE ilkesi (İngilizce) | Türkçe karşılığı | Neden böyle |
|---|---|---|---|
| 1 | Cümle ≤20 / ≤25 kelime | ≤15 / ≤18 kelime | Türkçe sondan eklemelidir: edat, artikel ve yardımcı fiil eke girer, aynı içerik daha az kelime tutar. 18 sayısı bu skill'in sezgisel seçimidir (25'in yaklaşık 0,72'si). Paralel bir derlemle doğrulanmadı. `--max-words-tr` ile değişir. |
| 2 | Edilgen yok | Edilgen yok (öneri düzeyinde) | Türkçe talimat dili kişisiz edilgeni olağan sayar ("dosya kaydedilir"). Bu yüzden kural öneri düzeyindedir ve çıkış kodunu etkilemez. |
| 3 | Yalın zaman, present perfect yok | "-mektedir", "-mış bulunmaktadır", "-mış olup", "-mış olduğu" yok | Türkçede present perfect yoktur. Aynı yükü resmî yazının dolaylı zaman kalıpları taşır. |
| 4 | Phrasal verb yok | Deyimsel fiil yok | Phrasal verb'in Türkçe karşılığı, anlamı parçalarından çıkmayan fiil deyimidir ("ayağa kaldır"). |
| 5 | Fiil, isim değil | Fiil ismi + boş fiil yok | "incelemesi gerçekleştirildi", "güncelleme işlemi yapıldı" kalıbı İngilizce "perform an analysis" ile aynı sorundur. |
| 6 | Cümle başına tek talimat | Ulaç zinciri ve "olup" yok | İngilizce "and … then" zincirini Türkçe ulaçla kurar: -ıp, -arak, -dıktan sonra, -ınca, -ken. |
| 7 | Yalın, yaygın kelime | Ağdalı / resmî kelime yok | ASD sözlüğünün Türkçesi yoktur. Yerine dar bir "kullanma" listesi vardır. |
| 8 | Noktalı virgül yok | Aynı | Dilden bağımsız. |
| 9 | Kiplik korunur | Aynı | "olabilir", "-ebilir", "muhtemelen" içeriktir. |

## Linter her kuralı nasıl tanır

Linter bir çözümleyici değildir: düzenli ifadeler ve ek kalıplarıyla çalışır. Türkçe metin
paragraf bazında taranır: satır sonunda bölünmüş bir cümle ya da kalıp birleştirilip öyle okunur.

**Tablo 2 (v1.0) — Türkçe kuralların tanıma yöntemi ve kör noktaları**

| # | Kural kimliği | Düzey | Nasıl tanır | Bilinen kör nokta |
|---|---|---|---|---|
| 1 | `semicolon` | sert | `;` karakteri. Kod bloğu ve satır içi kod atlanır. | Yok. |
| 2 | `long-sentence` | sert | Cümleyi `. ! ?` ile böler, boşlukla ayrılmış kelimeleri sayar. Sıra sayısı ("3. satır") ve kısaltma ("vb.") cümle bitirmez. | "·" ile ayrılmış sütun listesi tek cümle sayılır. Etiket satırı ":" ile bitmiyorsa alttaki paragrafa eklenir. |
| 3 | `passive-voice` | öneri | Edilgen eki + çekim eki: ünsüzden sonra -Il, l'den sonra -In, ünlüden sonra -n (-lAn ve dar bir kök listesi). "tarafından". | Kişisiz edilgeni de işaretler. Türkçe prosedür metninde 100 kelimede 3–5 bulgu çıkar. Sıfatlaşmış biçimleri de işaretler ("aranabilir"). Edilgen ulaç ("kullanılarak") ve -An ortacı ("belirtilen") işaretlenmez. |
| 4 | `compound-tense` | öneri | "-mAktA(dIr)", "-mIş/-AcAk/-yor" + "olup / olacak / bulunmaktadır / durumda / olduğu". | "gerekmektedir" gibi alıntı içindeki örnekleri de işaretler. |
| 5 | `nominalization` | sert | Fiil ismi (-mA, -mAsI, bazı -Im/-Iş) + "yap- / gerçekleştir- / icra et- / yerine getir-", "… işlemi yap-", "-mAsI sağlan-", "tabi tut-", "-nIn yapılması". | Fiil ismi listede olmayan bir -Im ise ("değerlendirim") kaçar. "toplantı yap-" bilerek işaretlenmez. |
| 6 | `marketing-adjective` | sert | Kelime listesi. | Listede olmayan sıfat kaçar. "benzersiz" yalnız bir ürün ismi önünde işaretlenir (veritabanı anlamı korunur). |
| 7 | `phrasal-verb` | sert | Deyim listesi, fiil çekimli. | Gerçek anlamı ayırt edemez ("tableti masaya yatır"). Listede olmayan deyim kaçar. Projenin kendi terimi için `--allow`. |
| 8 | `bureaucratic` | sert | Kelime listesi, her biri gündelik karşılığıyla. | Listede olmayan kelime kaçar. |
| 9 | `clause-chain` | sert | "olup" her zaman. Bir cümlede iki ya da daha çok ulaç. "olup olmadığı", "uyup uymadığı" sayılmaz. | Ulaçsız kurulan zinciri görmez ("sağlıyor, … hedefliyoruz"). |
| 10 | `synonym-rotation` | sert | 14 fiil grubu, dosya genelinde. | Yalnız listedeki fiil çiftleri. İsimlerde dönüşü ("kullanıcı / müşteri") görmez. Aynı fiilin iki ayrı anlamını ayırt edemez. |
| 11 | `dangling-conjunction` | sert | Liste maddesi "ve / veya / ya da / yahut" ile bitiyor. | Yok. |

Linter'ın hiç bakmadığı kurallar: eksiltme, isim yığını, paragraf başına tek konu, sözlük uyumu.
Bunlar okuyanın işidir.

## Ölçülen doğruluk (2026-10-06)

Altı ayrı ölçüm var. Hiçbiri tek başına "doğruluk oranı" değildir. Birlikte okunmalı.

**Tablo 3 (v1.0) — Test setleri ve sonuçları**

| # | Ölçüm | Kapsam | Sonuç | Ne söyler, ne söylemez |
|---|---|---|---|---|
| 1 | Regresyon (`tests/cases.json`) | 67 vaka, 81 etiket | 81 / 81 | Linter'la birlikte yazıldı. Bozulmayı yakalar, doğruluğu ölçmez. |
| 2 | Kör set, ayarsız ilk koşu (`tests/heldout.json`) | 224 vaka. Linter'ı görmeyen ayrı bir ajan yazdı. | Beklenen 137 bulgunun 130'u yakalandı. 520 yasak etiketten 2 yanlış alarm. | Seti yazan da linter'ı yazan da aynı model ailesi. Kelime dağarcığı örtüşür, bu yüzden liste tabanlı kurallarda oran şişkindir. |
| 3 | Kör set, düzeltmelerden sonra | Aynı 224 vaka | 136 / 137, 2 / 520 | Düzeltmeler bu sete bakılarak yapıldı. Set artık kör değildir. Kalan 3 hata bilinen sınırdır (2 gerçek anlamlı deyim, 1 "yaz / gir" dönüşü). |
| 4 | İngilizce birebirlik (`run_tests.py --parity`) | Upstream'in 5 dosyası, 130 bulgu | Hepsi upstream `ste-lint.py` ile aynı | Türkçe eklenirken İngilizce davranış değişmedi. |
| 5 | Gerçek metin, örneklem etiketleme | Daha önce taranmamış 6 SKILL.md, 9.961 kelime, 737 bulgu. 76'sı elle etiketlendi. | 76 bulgunun 67'si doğru | Asıl gösterge budur. Ayrıntı Tablo 4'te. |
| 6 | Gerçek metin, kaçan sayımı | Bir proje tanım dokümanı şablonunun standart metinleri (78 satır), elle okundu | Yapısal kurallar: kaçan bulunmadı. Liste tabanlı kurallar: 7 sorunun 2'si yakalandı, 5'i kaçtı | İlk temasta liste tabanlı kurallar gerçek metindeki sorunların üçte birini görür. Kaçan 5 kalıp sonradan eklendi. |

**Tablo 4 (v1.0) — Gerçek metinde kural bazında isabet (6 dosya, 76 etiketli bulgu)**

| # | Kural | Toplam bulgu | Etiketlenen | Doğru | Yanlışların nedeni |
|---|---|---|---|---|---|
| 1 | `semicolon` | 247 | — | — | Mekanik. Etiketlenmedi. |
| 2 | `passive-voice` | 333 | 20 | 18 | "salt okunur", "aranabilir" (sıfat). İlki sonra düzeltildi. |
| 3 | `long-sentence` | 121 | 20 | 18 | "·" ile ayrılmış iki sütun listesi. |
| 4 | `phrasal-verb` | 13 | 13 | 13 | Hepsi "top kimde", "dürt", "dile getir", "gözden kaç". İlk ikisi projenin kendi terimidir: `--allow`. |
| 5 | `synonym-rotation` | 6 | 6 | 5 | "bildir" iki ayrı bağlamda. |
| 6 | `nominalization` | 5 | 5 | 5 | — |
| 7 | `clause-chain` | 5 | 5 | 4 | Kalın yazıdan sonraki nokta cümle sonu sayılmadı. Sonra düzeltildi. |
| 8 | `compound-tense` | 3 | 3 | 3 | — |
| 9 | `marketing-adjective` | 3 | 3 | 0 | Üçü de "benzersiz" (veritabanı anlamı). Sonra düzeltildi. |
| 10 | `bureaucratic` | 1 | 1 | 1 | — |

Tablo 4'teki "sonra düzeltildi" notlu üç düzeltme yapıldıktan sonra gerçek metinde yeniden
etiketleme yapılmadı.

## Sonuç: ne beklenmeli

- **Yapısal kurallar güvenilir.** Noktalı virgül, cümle uzunluğu, "olup", ulaç zinciri, birleşik
  zaman, liste sonu bağlacı. Hem kör sette hem gerçek metinde yakalama ve isabet yüksek.
- **Edilgen kuralı doğru ama gürültülü.** Biçimi iyi tanır. Türkçe prosedür dili edilgeni çok
  kullandığı için bulgu sayısı yüksektir. Öneri düzeyinde kalması bu yüzden.
- **Liste tabanlı kurallar isabetli ama eksik.** Pazarlama sıfatı, deyim, ağdalı kelime ve
  isimleştirme: işaretlediği genellikle doğrudur, işaretlemediği çok şey vardır. Liste, gerçek
  metinde kaçan gördükçe büyür.
- **Anlam gerektiren iş linter'da yok.** Gerçek anlam / deyim ayrımı, iki fiilin aynı işi anlatıp
  anlatmadığı, faili bilinmeyen edilgen. Bunlar skill'i uygulayan modelin işidir.

## Listeyi büyütme

Gerçek bir metinde kaçan bir kalıp görürsen:

1. Kalıbı `scripts/sade-lint.py` içindeki ilgili listeye ekle (`_TR_BUREAUCRATIC`, `_TR_MARKETING`,
   `_TR_IDIOM`, `_TR_NOMINAL`, `TR_SYNONYM_GROUPS`).
2. `tests/cases.json` içine bir "yakalamalı" ve bir "yakalamamalı" vaka ekle.
3. `python scripts/sade-lint.py --selftest` ve `python tests/run_tests.py` çalıştır. İkisi de
   temiz geçmeli.
4. `python tests/run_tests.py --measure tests/heldout.json` sonucunun kötüleşmediğini kontrol et.
