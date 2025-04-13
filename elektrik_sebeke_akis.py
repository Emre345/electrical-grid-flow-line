import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

class ElektrikSebekesi:
    """Elektrik şebekesi akış optimizasyonu modeli"""
    
    def __init__(self, ad="Test Şebekesi"):
        """Elektrik şebekesi nesnesini başlat."""
        self.ad = ad
        self.G = nx.DiGraph(name=ad)
        self.sonuclar = {}
        
    def dugum_ekle(self, dugum_id, talep=0, uretim=0):
        """Şebekeye bir düğüm ekle.
        
        Args:
            dugum_id: Düğüm kimliği
            talep: Elektrik talebi (MW)
            uretim: Elektrik üretimi (MW)
        """
        net_deger = uretim - talep
        
        if net_deger > 0:
            dugum_tipi = "kaynak"
        elif net_deger < 0:
            dugum_tipi = "hedef"
        else:
            dugum_tipi = "transfer"
            
        self.G.add_node(
            dugum_id,
            talep=talep,
            uretim=uretim,
            net=net_deger,
            tip=dugum_tipi
        )
        return self
        
    def hat_ekle(self, kaynak, hedef, kapasite, maliyet, akis=0):
        """Şebekeye bir iletim hattı ekle.
        
        Args:
            kaynak: Kaynak düğüm ID
            hedef: Hedef düğüm ID
            kapasite: Hat kapasitesi (MW)
            maliyet: Birim akış maliyeti
            akis: Başlangıç akış değeri (varsayılan: 0)
        """
        self.G.add_edge(kaynak, hedef, kapasite=kapasite, maliyet=maliyet, akis=akis)
        return self
    
    def akis_ata(self, kaynak, hedef, akis_degeri):
        """Belirli bir hatta akış değeri ata.
        
        Args:
            kaynak: Kaynak düğüm ID
            hedef: Hedef düğüm ID
            akis_degeri: Atanacak akış değeri (MW)
        """
        if self.G.has_edge(kaynak, hedef):
            self.G[kaynak][hedef]['akis'] = akis_degeri
        else:
            print(f"Hata: {kaynak} ve {hedef} arasında hat bulunamadı.")
        return self
        
    def min_maliyet_akis_hesapla(self):
        """Minimum maliyetli akış hesapla.
        
        Returns:
            akislar: Kenar akışlarını içeren sözlük
            toplam_maliyet: Toplam akış maliyeti
        """
        try:
            # NetworkX için özel bir optimizasyon grafiği oluştur
            mcf_graph = nx.DiGraph()
            
            # Düğümleri ekle ve demand (arz/talep) değerlerini ayarla
            for node, attr in self.G.nodes(data=True):
                # Kaynak düğümler negatif demand (arz), hedef düğümler pozitif demand (talep)
                if attr['tip'] == 'kaynak':
                    mcf_graph.add_node(node, demand=-attr['net'])
                elif attr['tip'] == 'hedef':
                    mcf_graph.add_node(node, demand=abs(attr['net']))
                else:
                    mcf_graph.add_node(node, demand=0)
            
            # Kenarları ekle
            for u, v, data in self.G.edges(data=True):
                mcf_graph.add_edge(u, v, capacity=data['kapasite'], weight=data['maliyet'])
            
            # Minimum maliyetli akış hesapla
            flow_cost, flow_dict = nx.network_simplex(mcf_graph)
            
            # Akış sonuçlarını orijinal grafikteki "akis" özelliğine aktar
            for u, v, data in self.G.edges(data=True):
                if (u, v) in flow_dict:
                    self.G[u][v]['akis'] = flow_dict[(u, v)]
                else:
                    self.G[u][v]['akis'] = 0
            
            # Sonuçları sözlük formatında hazırla
            akislar = {}
            for u, v, data in self.G.edges(data=True):
                if u not in akislar:
                    akislar[u] = {}
                akislar[u][v] = data['akis']
            
            # Sonuçları sakla
            self.sonuclar['akislar'] = akislar
            self.sonuclar['toplam_maliyet'] = flow_cost
            
            return akislar, flow_cost
            
        except Exception as e:
            print(f"Hata: Akış hesaplanırken bir sorun oluştu: {e}")
            return {}, 0
            
    def darbogazlari_bul(self, esik_yuzdesi=90):
        """Şebekedeki darboğazları tespit et.
        
        Args:
            esik_yuzdesi: Darboğaz sayılması için kapasitenin kullanım yüzdesi eşiği
            
        Returns:
            darbogazlar: Darboğaz hatlarının listesi
        """
        darbogazlar = []
        
        for u, v, data in self.G.edges(data=True):
            kapasite = data['kapasite']
            akis = data['akis']
            
            if kapasite > 0:  # Sıfır kapasiteli hatları atla
                kullanim_yuzdesi = (akis / kapasite) * 100
                if kullanim_yuzdesi >= esik_yuzdesi:
                    darbogazlar.append({
                        'hat': (u, v),
                        'kapasite': kapasite,
                        'akis': akis,
                        'kullanim_yuzdesi': kullanim_yuzdesi
                    })
                    
        # Kullanım yüzdesine göre sırala
        darbogazlar.sort(key=lambda x: x['kullanim_yuzdesi'], reverse=True)
        return darbogazlar
        
    def gorselleştir(self, akislari_goster=True):
        """Şebekeyi görselleştir."""
        plt.figure(figsize=(10, 8))
        
        # Düğüm pozisyonlarını belirle
        pos = nx.spring_layout(self.G, seed=42)
        
        # Düğüm tipine göre renkler
        dugum_renkleri = []
        for n in self.G.nodes():
            if self.G.nodes[n]['tip'] == 'kaynak':
                dugum_renkleri.append('green')
            elif self.G.nodes[n]['tip'] == 'hedef':
                dugum_renkleri.append('red')
            else:
                dugum_renkleri.append('blue')
                
        # Düğümleri çiz
        nx.draw_networkx_nodes(
            self.G,
            pos,
            node_color=dugum_renkleri,
            node_size=300,
            alpha=0.8
        )
        
        # Düğüm etiketleri
        dugum_etiketleri = {}
        for n in self.G.nodes():
            dugum_etiketleri[n] = f"{n}\nÜretim: {self.G.nodes[n]['uretim']}\nTalep: {self.G.nodes[n]['talep']}"
        
        nx.draw_networkx_labels(self.G, pos, labels=dugum_etiketleri, font_size=8)
        
        # Kenarları çiz
        if akislari_goster:
            # Akış değerlerine göre kenar kalınlıkları
            kalinliklar = []
            kenar_renkleri = []
            
            for u, v, data in self.G.edges(data=True):
                kapasite = data['kapasite']
                akis = data['akis']
                
                # Kenar kalınlığı
                if kapasite > 0:
                    kalinlik = (akis / kapasite) * 2 + 0.5
                    
                    # Doluluk oranına göre renk
                    doluluk_orani = akis / kapasite
                    if doluluk_orani >= 0.9:  # %90 ve üzeri kırmızı
                        kenar_renkleri.append('red')
                    elif doluluk_orani >= 0.7:  # %70-%90 arası turuncu
                        kenar_renkleri.append('orange')
                    else:  # %70 altı yeşil
                        kenar_renkleri.append('green')
                else:
                    kalinlik = 0.5
                    kenar_renkleri.append('gray')
                    
                kalinliklar.append(kalinlik)
                
            # Kenarları çiz
            nx.draw_networkx_edges(
                self.G,
                pos,
                width=kalinliklar,
                edge_color=kenar_renkleri,
                alpha=0.7,
                arrowsize=15
            )
            
            # Kenar etiketleri
            kenar_etiketleri = {}
            for u, v, data in self.G.edges(data=True):
                kenar_etiketleri[(u, v)] = f"Akış: {data['akis']:.1f}\nKap: {data['kapasite']}\nMaliyet: {data['maliyet']}"
                
            nx.draw_networkx_edge_labels(
                self.G,
                pos,
                edge_labels=kenar_etiketleri,
                font_size=7
            )
        else:
            # Sadece kenarları çiz
            nx.draw_networkx_edges(self.G, pos, width=1.0, alpha=0.7, arrowsize=15)
            
            # Kenar etiketleri (akış olmadan)
            kenar_etiketleri = {}
            for u, v, data in self.G.edges(data=True):
                kenar_etiketleri[(u, v)] = f"Kap: {data['kapasite']}\nMaliyet: {data['maliyet']}"
                
            nx.draw_networkx_edge_labels(
                self.G,
                pos,
                edge_labels=kenar_etiketleri,
                font_size=8
            )
            
        plt.title(f"Elektrik Şebekesi: {self.ad}")
        plt.axis('off')
        plt.tight_layout()
        plt.show()
        
    def rapor_olustur(self):
        """Şebeke analiz raporu oluştur."""
        print(f"===== {self.ad} - ŞEBEKE ANALİZ RAPORU =====\n")
        
        # Şebeke özeti
        print(f"ŞEBEKE ÖZETİ:")
        print(f" Düğüm sayısı: {self.G.number_of_nodes()}")
        print(f" Hat sayısı: {self.G.number_of_edges()}")
        
        # Düğüm tipleri
        kaynak_sayisi = len([n for n, attr in self.G.nodes(data=True) if attr['tip'] == 'kaynak'])
        hedef_sayisi = len([n for n, attr in self.G.nodes(data=True) if attr['tip'] == 'hedef'])
        transfer_sayisi = len([n for n, attr in self.G.nodes(data=True) if attr['tip'] == 'transfer'])
        
        print(f" Kaynak düğümler: {kaynak_sayisi}")
        print(f" Hedef düğümler: {hedef_sayisi}")
        print(f" Transfer düğümleri: {transfer_sayisi}\n")
        
        # Toplam üretim ve talep
        toplam_uretim = sum(attr['uretim'] for _, attr in self.G.nodes(data=True))
        toplam_talep = sum(attr['talep'] for _, attr in self.G.nodes(data=True))
        
        print(f" Toplam üretim kapasitesi: {toplam_uretim:.2f} MW")
        print(f" Toplam talep: {toplam_talep:.2f} MW\n")
        
        # Akış sonuçları
        if 'toplam_maliyet' in self.sonuclar:
            print("AKIŞ SONUÇLARI:")
            print(f" Toplam akış maliyeti: {self.sonuclar['toplam_maliyet']:.2f}\n")
        
        # Darboğazlar
        darbogazlar = self.darbogazlari_bul()
        if darbogazlar:
            print("DARBOĞAZ ANALİZİ:")
            print(f" Tespit edilen darboğaz sayısı: {len(darbogazlar)}")
            print("\n En kritik darboğazlar:")
            
            for i, db in enumerate(darbogazlar[:5], 1):  # İlk 5 darboğazı göster
                print(f" {i}. Hat {db['hat']}: Kapasite {db['kapasite']:.2f} MW, "
                      f"Akış {db['akis']:.2f} MW, Kullanım: %{db['kullanim_yuzdesi']:.1f}")
                      
        print("\n=============================================")

def ornek_sebeke_olustur():
    """Basit bir örnek elektrik şebekesi oluştur."""
    sebeke = ElektrikSebekesi("Basit Örnek Şebeke")
    
    # Düğümleri ekle: (id, talep, üretim)
    sebeke.dugum_ekle("A", 0, 100)    # Üretim tesisi
    sebeke.dugum_ekle("B", 0, 150)    # Üretim tesisi
    sebeke.dugum_ekle("C", 50, 0)     # Talep merkezi
    sebeke.dugum_ekle("D", 120, 0)    # Talep merkezi
    sebeke.dugum_ekle("E", 80, 0)     # Talep merkezi
    sebeke.dugum_ekle("F", 0, 0)      # Transfer merkezi
    
    # Hatları ekle: (kaynak, hedef, kapasite, maliyet, akış)
    sebeke.hat_ekle("A", "F", 80, 2, 30)
    sebeke.hat_ekle("A", "C", 40, 3, 20)
    sebeke.hat_ekle("B", "F", 60, 1, 25)
    sebeke.hat_ekle("B", "D", 90, 2, 40)
    sebeke.hat_ekle("F", "C", 30, 1, 15)
    sebeke.hat_ekle("F", "D", 50, 3, 20)
    sebeke.hat_ekle("F", "E", 80, 2, 30)
    
    return sebeke

def main():
    """Ana program."""
    print("ŞEBEKE AKIŞ PROBLEMİ ÇÖZÜCÜ\n")
    
    # Örnek şebeke oluştur
    sebeke = ornek_sebeke_olustur()
    print(f"{sebeke.ad} oluşturuldu.\n")
    
    # Şebekeyi görselleştir (belirlenen başlangıç akışlarıyla)
    print("Şebeke yapısını ve başlangıç akışlarını görselleştiriliyor...")
    sebeke.gorselleştir(akislari_goster=True)
    
    # Manuel olarak bazı akışları değiştir
    sebeke.akis_ata("A", "F", 45)
    sebeke.akis_ata("B", "D", 60)
    print("\nBazı hatların akış değerleri manuel olarak değiştirildi.")
    
    # Değiştirilen akışları görselleştir
    print("Manuel değiştirilmiş akışlar görselleştiriliyor...")
    sebeke.gorselleştir(akislari_goster=True)
    
    # Minimum maliyetli akış hesapla
    print("\nMinimum maliyetli akış hesaplanıyor...")
    akislar, maliyet = sebeke.min_maliyet_akis_hesapla()
    print(f"Toplam maliyet: {maliyet:.2f}")
    
    # Akışları görselleştir
    print("\nOptimum akışlar görselleştiriliyor...")
    sebeke.gorselleştir()
    
    # Darboğazları bul
    print("\nDarboğazlar tespit ediliyor...")
    darbogazlar = sebeke.darbogazlari_bul()
    print(f"{len(darbogazlar)} darboğaz tespit edildi.")
    
    for i, db in enumerate(darbogazlar, 1):
        print(f"{i}. Hat {db['hat']}: %{db['kullanim_yuzdesi']:.1f} kullanım")
    
    # Şebeke raporu
    print("\nŞebeke raporu oluşturuluyor...")
    sebeke.rapor_olustur()

if __name__ == "__main__":
    main()