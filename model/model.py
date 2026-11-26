from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self.lista_escursioni_parco = []

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        for r in relazioni:     # relazioni è una lista di dizionari [{"id_escur": 1, "id_p_int": 3}, {...}]
            id_escurione = r["id_escursione"]
            id_punto_interesse = r["id_punto_interesse"]

            for escursione in self.escursioni_map.values():
                if escursione.id == id_escurione:
                    escursione.punti_interesse.add(self.punti_interesse_map[id_punto_interesse])

            for punto_interesse in self.punti_interesse_map.values():
                if punto_interesse.id == id_punto_interesse:
                    punto_interesse.escursioni.add(self.escursioni_map[id_escurione])

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        # Lista delle sole escursioni del parco scelto
        self.carica_lista_escursioni_parco(id_parco)

        self._ricorsione(0, [], 0, 0, 0, set(), max_giorni, max_budget)

        if self._valore_ottimo == -1:
            return [], 0, 0

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set, max_giorni, max_budget):
        """" Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # --- A) VALUTO IL PACCHETTO CORRENTE ---
        # Ogni pacchetto che arriva qui è già valido, perché i limiti vengono
        # controllati PRIMA di aggiungere un'escursione. Se è migliore dell'ottimo
        # trovato finora, lo salvo. Uso .copy() perché pacchetto_parziale verrà
        # modificato dal backtracking e perderei il risultato
        if valore_corrente > self._valore_ottimo:
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._valore_ottimo = valore_corrente
            self._costo = costo_corrente

        # --- B) PROVO AD AGGIUNGERE UNA NUOVA ESCURSIONE ---
        # Parto da start_index e non da 0: considero solo le escursioni successive
        # all'ultima scelta, così ogni combinazione è generata una sola volta
        # ({A,B} e {B,A} sono lo stesso pacchetto).
        # La terminazione è implicita, se start_index == len(lista), il for non
        # esegue nulla e la funzione ritorna
        for i in range(start_index, len(self.lista_escursioni_parco)):
            escursione = self.lista_escursioni_parco[i]

            # Calcolo durata e costo che avrei DOPO l'aggiunta, senza modificare
            # le variabili correnti (quindi non c'è nulla da ripristinare)
            nuova_durata = durata_corrente + escursione.durata_giorni
            nuovo_costo = costo_corrente + escursione.costo

            # Se l'aggiunta sfora un limite di giorni o costo, salto questa escursione
            if not self.escursione_rispetta_limiti(nuova_durata, nuovo_costo, max_giorni, max_budget):
                continue

            # Punti di interesse di questa escursione NON ancora coperti dal pacchetto:
            # un punto già incluso non porta voto una seconda volta
            nuovi_punti = {p for p in escursione.punti_interesse if p not in punti_usati}

            # Voto aggiunto è la somma dei voti dei soli punti nuovi
            somma_voti = sum(self.punti_interesse_map[p.id].voto_visitatori for p in nuovi_punti)

            # --- SCELTA: aggiungo l'escursione al pacchetto ---
            pacchetto_parziale.append(escursione)
            punti_usati.update(nuovi_punti)

            # --- RICORSIONE: continuo dal pacchetto esteso ---
            # con i + 1 la chiamata successiva considera solo le escursioni dopo questa
            self._ricorsione(i + 1, pacchetto_parziale, nuova_durata, nuovo_costo, valore_corrente + somma_voti, punti_usati, max_giorni, max_budget)

            # --- BACKTRACKING: annullo la scelta ---
            # Tolgo solo i punti aggiunti da questo livello (non quelli dei livelli
            # superiori) e l'ultima escursione, così il ciclo può provare un'altra strada
            punti_usati.difference_update(nuovi_punti)
            pacchetto_parziale.pop()

    @staticmethod
    def escursione_rispetta_limiti(durata, costo, max_giorni, max_budget):
        if max_giorni is not None and durata > max_giorni:
            return False
        if max_budget is not None and costo > max_budget:
            return False
        return True

    def carica_lista_escursioni_parco(self, id_parco):
        # Svuoto la lista per evitare duplicati
        self.lista_escursioni_parco.clear()
        for escursione in self.escursioni_map.values():
            if escursione.id_parco == id_parco:
                self.lista_escursioni_parco.append(escursione)




if __name__ == '__main__':

    m = Model()
