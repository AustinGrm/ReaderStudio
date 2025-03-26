class BookIndexerError(Exception):
    """Base exception for book indexer"""
    pass

class MetadataExtractionError(BookIndexerError):
    """Failed to extract metadata"""
    pass

class FileOperationError(BookIndexerError):
    """Failed to perform file operation"""
    pass 