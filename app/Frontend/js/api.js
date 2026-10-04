/* ==========================================================
   PlagiCheck - Module de communication API sécurisée
   ==========================================================
   Ce fichier centralise tous les appels au backend.
   Il gère automatiquement :
   - Le stockage sécurisé du jeton JWT (sessionStorage).
   - L'ajout de l'en-tête Authorization sur chaque requête.
   - La déconnexion automatique si le jeton est expiré.
*/

const API_BASE_URL = "http://127.0.0.1:8000";

// --- Gestion du Jeton JWT ---

const Auth = {
    // Sauvegarder le jeton après une connexion réussie
    sauvegarderJeton(jeton) {
        sessionStorage.setItem("plagicheck_jeton", jeton);
    },

    // Récupérer le jeton
    obtenirJeton() {
        return sessionStorage.getItem("plagicheck_jeton");
    },

    // Supprimer le jeton (déconnexion)
    supprimerJeton() {
        sessionStorage.removeItem("plagicheck_jeton");
    },

    // Vérifier si l'utilisateur est connecté
    estConnecte() {
        return this.obtenirJeton() !== null;
    },

    // Récupérer les infos utilisateur stockées
    obtenirUtilisateur() {
        const user = sessionStorage.getItem("plagicheck_utilisateur");
        return user ? JSON.parse(user) : null;
    },

    // Sauvegarder les infos utilisateur
    sauvegarderUtilisateur(utilisateur) {
        sessionStorage.setItem("plagicheck_utilisateur", JSON.stringify(utilisateur));
    },

    // Supprimer les infos utilisateur
    supprimerUtilisateur() {
        sessionStorage.removeItem("plagicheck_utilisateur");
    }
};

// --- Fonction d'appel API sécurisée ---

async function appelAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Préparation des en-têtes
    const headers = options.headers || {};
    
    // Si on a un jeton, on l'ajoute automatiquement
    const jeton = Auth.obtenirJeton();
    if (jeton) {
        headers["Authorization"] = `Bearer ${jeton}`;
    }

    // Si on envoie des données JSON, on précise le type
    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(options.body);
    }

    try {
        const reponse = await fetch(url, { ...options, headers });

        // Si le jeton est expiré ou invalide (401), on déconnecte l'utilisateur
        if (reponse.status === 401) {
            const erreur = await reponse.json().catch(() => ({ detail: "Erreur 401" }));
            // Ne pas déconnecter si on est en train d'essayer de se connecter
            if (!endpoint.includes("/auth/connexion")) {
                Auth.supprimerJeton();
                Auth.supprimerUtilisateur();
                window.location.href = "/app/connexion.html";
            }
            throw new Error(erreur.detail || "Session expirée. Veuillez vous reconnecter.");
        }
        // Si le serveur refuse l'accès (403)
        if (reponse.status === 403) {
            const erreur = await reponse.json().catch(() => ({ detail: "Accès refusé" }));
            throw new Error(erreur.detail || "Accès refusé");
        }

        // Si le serveur renvoie une erreur (400, 404, 500...)
        if (!reponse.ok) {
            const erreur = await reponse.json().catch(() => ({ detail: "Erreur serveur" }));
            throw new Error(erreur.detail || "Une erreur est survenue");
        }

        // Si la réponse est vide (ex: 204 No Content)
        if (reponse.status === 204) {
            return null;
        }

        return await reponse.json();

    } catch (erreur) {
        console.error("Erreur API :", erreur);
        throw erreur;
    }
}

// --- Fonctions d'authentification ---

async function seConnecter(email, motDePasse) {
    const donnees = await appelAPI("/auth/connexion", {
        method: "POST",
        body: { email, mot_de_passe: motDePasse }
    });

    if (donnees && donnees.jeton_acces) {
        Auth.sauvegarderJeton(donnees.jeton_acces);
        Auth.sauvegarderUtilisateur(donnees.utilisateur);
        return donnees.utilisateur;
    }
    throw new Error("Réponse de connexion invalide");
}

async function sInscrire(nom, email, motDePasse) {
    // Note : le rôle n'est PAS envoyé. Le serveur force "etudiant".
    return await appelAPI("/auth/inscription", {
        method: "POST",
        body: { nom, email, mot_de_passe: motDePasse }
    });
}

async function seDeconnecter() {
    // On appelle la route de déconnexion pour révoquer le jeton côté serveur
    try {
        await appelAPI("/auth/deconnexion", { method: "POST" });
    } catch (e) {
        // On ignore les erreurs de réseau lors de la déconnexion
    } finally {
        Auth.supprimerJeton();
        Auth.supprimerUtilisateur();
        window.location.href = "/app/connexion.html";
    }
}

// Rendre les fonctions accessibles globalement pour les autres scripts
window.Auth = Auth;
window.appelAPI = appelAPI;
window.seConnecter = seConnecter;
window.sInscrire = sInscrire;
window.seDeconnecter = seDeconnecter;