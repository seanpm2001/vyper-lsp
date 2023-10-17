from typing import Optional
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DECLARATION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
)
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
from pygls.workspace import Document
from vyper_lsp.analyzer.AstAnalyzer import AstAnalyzer
from vyper_lsp.analyzer.SourceAnalyzer import SourceAnalyzer

from vyper_lsp.completer.completer import Completer
from vyper_lsp.navigation import ASTNavigator
from vyper_lsp.utils import extract_enum_name

from .ast import AST

server = LanguageServer("vyper", "v0.0.1")
completer = Completer()
navigator = ASTNavigator()
ast_analyzer = AstAnalyzer()
source_analyzer = SourceAnalyzer()

ast = AST()

def validate_doc(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    source_diagnostics = source_analyzer.get_diagnostics(text_doc)
    # ast_diagnostics = ast_analyzer.get_diagnostics(text_doc)
    ast_diagnostics = []
    ls.publish_diagnostics(
        params.text_document.uri, source_diagnostics + ast_diagnostics
    )
    ast.update_ast(text_doc)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    doc: Document = ls.workspace.get_document(params.text_document.uri)
    version_pragma = source_analyzer.get_version_pragma(doc)
    ls.show_message(f"Version pragma: {version_pragma}")
    validate_doc(ls, params)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    # validate_doc(ls, params)
    pass

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


@server.feature(TEXT_DOCUMENT_DEFINITION)
def go_to_definition(
    ls: LanguageServer, params: DefinitionParams
) -> Optional[Location]:
    # TODO: Look for assignment nodes to find definition
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_declaration(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)


def get_enum_name(ls: LanguageServer, doc: Document, variant_line_no: int):
    for line_no in range(variant_line_no, 0):
        line = doc.lines[line_no]
        enum_name = extract_enum_name(line)
        if enum_name:
            return enum_name


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
    server.start_io()
