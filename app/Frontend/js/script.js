/* ==========================================================
   PLAGICHECK
   FICHIER JAVASCRIPT
   ========================================================== */


/*
   Pour l'instant, le JavaScript reste volontairement simple.

   La connexion avec ton backend Python/FastAPI viendra
   lorsque nous commencerons l'intégration fonctionnelle
   de PlagiCheck.
*/


/* ==========================================================
   1. VÉRIFICATION DU CHARGEMENT
   ========================================================== */


/*
   Ce message apparaît dans la console du navigateur.

   Pour voir la console :
   F12 → Console
*/

console.log("PlagiCheck est correctement chargé.");



/* ==========================================================
   2. ANIMATION DES CARTES
   ========================================================== */


/*
   On récupère toutes les cartes utilisateurs
   et fonctionnalités.
*/

const cards = document.querySelectorAll(
    ".user-card, .feature-card"
);



/*
   On applique une petite animation lorsque
   la souris passe sur une carte.
*/

cards.forEach(function(card) {


    /* Lorsque la souris entre sur la carte */

    card.addEventListener(
        "mouseenter",
        function() {

            card.style.transform =
                "translateY(-3px)";

            card.style.transition =
                "0.2s";

        }
    );



    /* Lorsque la souris quitte la carte */

    card.addEventListener(
        "mouseleave",
        function() {

            card.style.transform =
                "translateY(0)";

        }
    );

});