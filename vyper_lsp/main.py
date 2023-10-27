import argparse
from typing import Optional
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DECLARATION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
)
from packaging.version import Version
from pygls.lsp.methods import HOVER, IMPLEMENTATION, TEXT_DOCUMENT_DID_SAVE
from pygls.lsp.types import (
    CompletionOptions,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
)
from pygls.lsp.types.language_features import (
    CompletionList,
    DeclarationParams,
    DefinitionParams,
    HoverParams,
    List,
    Location,
    Hover,
)
from pygls.server import LanguageServer
from vyper_lsp.analyzer.AstAnalyzer import AstAnalyzer
from vyper_lsp.analyzer.SourceAnalyzer import SourceAnalyzer
from vyper_lsp.debounce import Debouncer

from vyper_lsp.navigation import ASTNavigator
from vyper_lsp.utils import get_installed_vyper_version


from .ast import AST

ast = AST()

server = LanguageServer("vyper", "v0.0.1")
navigator = ASTNavigator(ast)

# AstAnalyzer is faster and better, but depends on the locally installed vyper version
# we should keep it around for now and use it when the contract version pragma is missing
# or if the version pragma matches the system version. its much faster so we can run it
# on every keystroke, with sourceanalyzer we should only run it on save
ast_analyzer = AstAnalyzer(ast)
completer = ast_analyzer
source_analyzer = SourceAnalyzer()


debouncer = Debouncer(wait=0.5)


def check_minimum_vyper_version():
    vy_version = get_installed_vyper_version()
    min_version = Version("0.3.7")
    if vy_version < min_version:
        raise Exception(
            f"vyper version {vy_version} is not supported, please upgrade to {min_version} or higher"
        )


@debouncer.debounce
def validate_doc(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    source_diagnostics = source_analyzer.get_diagnostics(text_doc)
    ast_diagnostics = ast_analyzer.get_diagnostics(text_doc)
    ls.publish_diagnostics(
        params.text_document.uri, source_diagnostics + ast_diagnostics
    )
    ast.update_ast(text_doc)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    check_minimum_vyper_version()
    ls.show_message("Vyper Language Server started")
    ls.show_message_log("Vyper Language Server started")
    validate_doc(ls, params)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    validate_doc(ls, params)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls: LanguageServer, params: DidSaveTextDocumentParams):
    validate_doc(ls, params)


@server.feature(
    TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[":", ".", "@", " "])
)
def completions(ls, params: CompletionParams) -> CompletionList:
    return completer.get_completions(ls, params)


@server.feature(TEXT_DOCUMENT_DECLARATION)
def go_to_declaration(
    ls: LanguageServer, params: DeclarationParams
) -> Optional[Location]:
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_declaration(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)
    else:
        ls.show_message("No declaration found")
        ls.show_message_log("No declaration found")


@server.feature(TEXT_DOCUMENT_DEFINITION)
def go_to_definition(
    ls: LanguageServer, params: DefinitionParams
) -> Optional[Location]:
    # TODO: Look for assignment nodes to find definition
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_declaration(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)


@server.feature(TEXT_DOCUMENT_REFERENCES)
def find_references(ls: LanguageServer, params: DefinitionParams) -> List[Location]:
    document = ls.workspace.get_document(params.text_document.uri)
    return [
        Location(uri=params.text_document.uri, range=range)
        for range in navigator.find_references(document, params.position)
    ]


@server.feature(HOVER)
def hover(ls: LanguageServer, params: HoverParams):
    document = ls.workspace.get_document(params.text_document.uri)
    hover_info = ast_analyzer.hover_info(document, params.position)
    if hover_info:
        return Hover(contents=hover_info, range=None)


@server.feature(IMPLEMENTATION)
def implementation(ls: LanguageServer, params: DefinitionParams):
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_implementation(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)


def main():
    parser = argparse.ArgumentParser(
        description="Start the server with specified protocol and options."
    )
    parser.add_argument("--stdio", action="store_true", help="Use stdio protocol")
    parser.add_argument(
        "--tcp",
        nargs=2,
        metavar=("HOST", "PORT"),
        help="Use TCP protocol with specified host and port",
    )

    args = parser.parse_args()

    if args.tcp:
        host, port = args.tcp
        server.start_tcp(host=host, port=int(port))
    else:
        # Default to stdio if --tcp is not provided
        server.start_io()
