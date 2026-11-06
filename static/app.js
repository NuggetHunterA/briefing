// Kleine Helfer im Browser: Alter der Ausgabe, aktuelle Rubrik, Live-Wetter.
(function () {
  "use strict";

  // Wie alt ist diese Ausgabe?
  var age = document.querySelector(".js-age");
  function updateAge() {
    if (!age) return;
    var mins = Math.round((Date.now() - new Date(age.dataset.generated).getTime()) / 60000);
    age.textContent = mins < 2 ? "gerade erschienen" : mins < 60 ? "vor " + mins + " Min." : "vor " + Math.round(mins / 60) + " Std.";
  }
  updateAge();
  setInterval(updateAge, 60000);

  // Aktive Rubrik in der Leiste markieren
  var links = Array.prototype.slice.call(document.querySelectorAll(".index a"));
  if ("IntersectionObserver" in window) {
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var a = byId[en.target.id];
        if (!a) return;
        links.forEach(function (l) { l.classList.toggle("on", l === a); });
        var nav = a.parentNode;
        if (nav.scrollWidth > nav.clientWidth) nav.scrollTo({ left: a.offsetLeft - (nav.clientWidth - a.offsetWidth) / 2, behavior: "smooth" });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    Object.keys(byId).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
  }

  // Stimmungsbild nur animieren, solange es sichtbar ist
  var mood = document.querySelector(".mood");
  if (mood && "IntersectionObserver" in window) {
    new IntersectionObserver(function (en) { mood.classList.toggle("paused", !en[0].isIntersecting); }).observe(mood);
  }

  // Aktuelle Werte direkt von Open-Meteo (erlaubt Browser-Zugriff); Vorhersage kommt aus der Ausgabe.
  var cfg = window.BRIEFING || {};
  var WMO = {0:"Klar",1:"Überwiegend klar",2:"Teils bewölkt",3:"Bedeckt",45:"Nebel",48:"Reifnebel",51:"Leichter Niesel",53:"Niesel",55:"Starker Niesel",56:"Gefrierender Niesel",57:"Gefrierender Niesel",61:"Leichter Regen",63:"Regen",65:"Starker Regen",66:"Gefrierender Regen",67:"Gefrierender Regen",71:"Leichter Schnee",73:"Schnee",75:"Starker Schnee",77:"Schneegriesel",80:"Regenschauer",81:"Regenschauer",82:"Heftige Schauer",85:"Schneeschauer",86:"Schneeschauer",95:"Gewitter",96:"Gewitter mit Hagel",99:"Gewitter mit Hagel"};
  var DIRS = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"];
  function fmt(v) { return String(Math.round(v)); }
  function set(key, text) {
    document.querySelectorAll('[data-live="' + key + '"]').forEach(function (el) { el.textContent = text; });
  }
  function live() {
    if (!cfg.lat || !window.fetch) return;
    var url = "https://api.open-meteo.com/v1/forecast?latitude=" + cfg.lat + "&longitude=" + cfg.lon +
      "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,relative_humidity_2m&timezone=Europe%2FBerlin";
    fetch(url).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || !d.current) return;
      var c = d.current;
      set("temp", fmt(c.temperature_2m) + "°");
      set("feels", fmt(c.apparent_temperature) + "°");
      set("cond", WMO[c.weather_code] || "");
      set("wind", fmt(c.wind_speed_10m) + " km/h " + DIRS[Math.floor(((c.wind_direction_10m || 0) + 22.5) / 45) % 8]);
      set("hum", fmt(c.relative_humidity_2m) + " %");
    }).catch(function () {});
  }
  live();
  setInterval(live, 15 * 60000);
})();
