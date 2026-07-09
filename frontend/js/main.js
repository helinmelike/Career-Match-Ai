// Giris noktasi. index.html buraya <script type="module" src="js/main.js">
// ile tek seferde bagliyor; her modul kendi window.* fonksiyonlarini kayit
// ettigi icin bu dosyanin govdesi bos - sadece import zincirini baslatiyor.
import './state.js';
import './render-helpers.js';
import './employer.js';
import './candidate.js';
