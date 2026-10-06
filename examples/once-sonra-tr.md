# Önce / Sonra — Türkçe

Örnekler bu skill için yazıldı. Gerçek bir sistemden ya da dokümandan alıntı değildir. Upstream
örneklerinin çevirisi de değildir. Kelime sayıları boşlukla ayrılmış parçalardır
(`metin.split()`).

## Örnek A — Tool açıklaması (Sıkı mod)

**Önce:**
> Bu araç, verilen klasördeki log dosyalarının taranması işlemini gerçekleştirecek olup, 30 günden
> eski olduğu tespit edilen dosyalar arşiv ayarının açık olması hâlinde arşive taşınır, aksi hâlde
> silinir; başka bir sürecin açık tuttuğu dosyalar ise atlanabilir.

**İşaretlenenler:** 35 kelimelik tek cümle (sınır 18) · "olup" · "taranması işlemini
gerçekleştirecek" (isimleştirme) · noktalı virgül · üç edilgen ("taranması", "silinir",
"atlanabilir"). Linter'ın işaretlemediği ama elle düzeltilen: "tespit edilen", "taşınır",
"olması hâlinde", "aksi hâlde".

Korunan: "atlanabilir" içindeki olasılık. Araç her açık dosyayı atlayacağını söylemiyor. Yeniden
yazım edilgeni etkene çevirir, "-ebilir" ekini bırakır.

**Sonra:**
> Araç, verilen klasördeki log dosyalarını tarar. Arşiv ayarı açıksa 30 günden eski dosyaları
> arşive taşır. Arşiv ayarı kapalıysa bu dosyaları siler. Başka bir sürecin açık tuttuğu dosyayı
> atlayabilir.

## Örnek B — Hata mesajı (Sıkı mod)

**Önce:**
> Ödeme işleminin gerçekleştirilmesi sırasında banka tarafından yanıt verilmemiş olması nedeniyle
> işleminiz tamamlanamamış olabilir; kartınızdan tutar çekilmiş olma ihtimali de bulunduğundan
> tekrar denemeden önce hesap hareketlerinizin kontrol edilmesi önerilmektedir.

**İşaretlenenler:** noktalı virgül · 28 kelime · "ödeme işleminin gerçekleştirilmesi"
(isimleştirme) · "banka tarafından" (fail belli, cümle yine de edilgen) · "önerilmektedir"
(birleşik zaman).

Linter'ın dokunmadığı: "olabilir" ve "ihtimali". Sistem ödemenin sonucunu bilmiyor. İki çekince
de bu bilgisizliğin doğru raporudur.

**Sonra:**
> Banka yanıt vermedi. Bu yüzden ödemeniz tamamlanmamış olabilir. Kartınızdan tutar çekilmiş
> olabilir. Tekrar denemeden önce hesap hareketlerinizi kontrol etmenizi öneririz.

"Ödemeniz tamamlanmadı" daha kısadır ama yanlıştır: sistemin bilmediği bir sonucu olgu diye
bildirir. "Kartınızdan tutar çekilmedi" de aynı hatadır. Zaman kuralı ile kiplik çatışırsa kiplik
kazanır. "önerilmektedir" emre çevrilmedi, "öneririz" oldu: kaynak öneriyor, zorunlu tutmuyor.

## Örnek C — Ajanlar arası talimat (Sıkı mod)

**Önce:**
> İnceleme ajanı, kendisine iletilen değişiklik isteğindeki dosyaları okuyarak test kapsamının
> yeterli olup olmadığını değerlendirdikten sonra bulgularını özet ajanına aktarmalı olup, 500
> satırı aşan değişikliklerde bazı dosyaların atlanmış olabileceği de bulgu listesinde
> belirtilmelidir.

**İşaretlenenler:** 32 kelime · "olup" · ulaç zinciri ("okuyarak", "değerlendirdikten sonra") ·
"belirtilmelidir" (edilgen). "olup olmadığını" işaretlenmez: soru anlamı taşır, cümle
birleştirmez. Linter'ın görmediği: "iletilen / aktarmalı" (aynı iş, iki fiil. "aktar" linter'ın
listesinde yok).

**Sonra:**
> Sana iletilen değişiklik isteğindeki dosyaları oku. Test kapsamının yeterli olup olmadığını
> değerlendir. Bulguları özet ajanına ilet. Değişiklik 500 satırı aşıyorsa bulgu listesine şunu
> yaz: bazı dosyalar atlanmış olabilir.

Korundu: "atlanmış olabilir". Kaynak dosyaları kimin atladığını söylemiyor, bu yüzden edilgen
kaldı. Atlamanın kesin olduğunu da söylemiyor, bu yüzden "olabilir" kaldı.

## Örnek D — Proje dokümanı varsayım maddesi (Sade mod)

**Önce:**
> Test ortamının kurulumu Yüklenici tarafından yapılacak olup, testlerde kullanılacak verinin
> Kurum tarafından proje başlangıç tarihinden önce hazır edileceği varsayılmıştır.

**İşaretlenenler:** 19 kelime · "olup" · iki "tarafından" (fail belli, cümle yine de edilgen).

**Sonra:**
> Yüklenici test ortamını kurar. Kurum'un test verisini proje başlangıç tarihinden önce
> hazırlayacağı varsayılmıştır.

Korundu: "varsayılmıştır". Varsayım maddesinde kimin varsaydığı bilerek söylenmez ve sözleşme
dilinde bu kalıp beklenir.

## Örnek E — Durum raporu (Sade mod)

**Önce:**
> Kusursuz altyapımız sayesinde deploy sürecini hayata geçirdik; ekip önce sonuçları kontrol
> etti, ardından müşteri çıktıyı doğruladı ve işbu rapor tarafınıza iletilmiştir.

**İşaretlenenler:** 21 kelime · "kusursuz" (pazarlama) · "hayata geçirdik" (deyim) · noktalı virgül ·
"kontrol etti / doğruladı" (aynı iş, iki fiil) · "işbu", "tarafınıza" (ağdalı) · "iletilmiştir"
(edilgen. Gönderen belli).

**Sonra:**
> Deploy sürecini başlattık. Ekip sonuçları kontrol etti. Sonra müşteri çıktıyı kontrol etti. Bu
> raporu size gönderiyoruz.

"Kusursuz altyapımız sayesinde" silindi: metin iddiayı kanıtlayan bir ölçüm vermiyor.

## Örnek F — Zaten uygun metin

> Dosyayı aç. 3. satırı oku. Değer boşsa işi durdur ve kullanıcıya bildir.

Değişiklik yok. "3." sıra sayısıdır, cümle bitirmez. Uygun metni zorla değiştirme.
