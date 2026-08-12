-- Copyright (c) Microsoft. All rights reserved.
-- Licensed under the MIT license. See LICENSE file in the project root for full license information.

{-# LANGUAGE QuasiQuotes, OverloadedStrings, RecordWildCards #-}

module Language.Bond.Codegen.Protobuf.Protobuf_proto
    ( protobuf_proto
    ) where

import Data.Char (toUpper)
import Data.Monoid
import Prelude
import Data.Text.Lazy (Text)
import qualified Data.Text.Lazy as LT
import Text.Shakespeare.Text
import Language.Bond.Syntax.Types
import qualified Language.Bond.Syntax.Types as BST
import Language.Bond.Syntax.Util
import Language.Bond.Util
import Language.Bond.Codegen.TypeMapping
import Language.Bond.Codegen.Util
import Language.Bond.Codegen.Protobuf.Util

protobuf_proto :: MappingContext -> String -> [Import] -> [Declaration] -> (String, Text)
protobuf_proto ctx _baseName imports declarations = (".proto", code)
  where
    code = [lt|syntax = "proto3";

package #{packageName};
#{importSection}#{declarationSection}|]

    packageName = sepBy "." toText $ getNamespace ctx

    importSection =
        let bondImports = map importLine imports
            emptyImport = if needsEmptyImport declarations
                          then [[lt|import "google/protobuf/empty.proto";|]]
                          else []
            allImports = emptyImport ++ bondImports
        in if null allImports then mempty
           else [lt|
#{newlineSep 0 id allImports}
|]

    importLine (Import path) =
        let protoPath = replaceExtension path
        in [lt|import "#{protoPath}";|]

    replaceExtension path =
        case reverse path of
            'd':'n':'o':'b':'.':rest -> reverse rest ++ ".proto"
            _ -> path ++ ".proto"

    declarationSection = newlineSep 0 (declToProto ctx) declarations

declToProto :: MappingContext -> Declaration -> Text
declToProto _ctx Struct{..}
    | not (null declParams) = error $ "Protobuf: generic struct '" ++ declName ++ "' cannot be converted to protobuf"
    | otherwise =
        let offset = fieldsStartFromZero structFields
            baseLine = case structBase of
                Nothing -> []
                Just (BT_UserDefined baseDecl _) ->
                    let baseName = BST.declName baseDecl
                        baseOrdinal = nextProtoFieldNum offset structFields
                    in [LT.pack $ "    " ++ baseName ++ " _base = " ++ show baseOrdinal ++ ";"]
                Just _ -> error $ "Protobuf: unsupported base type in struct '" ++ declName ++ "'"
            fieldLines = map (fieldToProto declName offset) structFields
        in [lt|
message #{declName} {
#{newlineSep 0 id (baseLine ++ fieldLines)}
}|]
  where
    nextProtoFieldNum _offsetByOne [] = 1 :: Int
    nextProtoFieldNum offsetByOne fs =
        let extra = if offsetByOne then 2 else 1
        in fromIntegral (maximum (map fieldOrdinal fs)) + extra

declToProto _ Enum{..} =
    let constants = reifyEnumValues enumConstants
        needsSentinel = case constants of
            (_, 0):_ -> False
            _        -> True
        sentinelName = map toUpper declName ++ "_UNSPECIFIED"
        sentinel = if needsSentinel
                   then [[lt|    #{sentinelName} = 0;|]]
                   else []
        constLines = map enumConstLine constants
        allLines = sentinel ++ constLines
    in [lt|
enum #{declName} {
#{newlineSep 0 id allLines}
}|]

declToProto _ Forward{..} = mempty

declToProto _ Alias{..} =
    error $ "Protobuf: type alias '" ++ declName ++ "' cannot be converted to protobuf"

declToProto _ctx Service{..}
    | not (null declParams) = error $ "Protobuf: generic service '" ++ declName ++ "' cannot be converted to protobuf"
    | otherwise =
        let methodLines = map methodToProto serviceMethods
        in [lt|
service #{declName} {
#{newlineSep 0 id methodLines}
}|]

fieldToProto :: String -> Bool -> Field -> Text
fieldToProto structName offsetByOne field =
    case protoFieldLine structName offsetByOne field of
        Left err -> error err
        Right s  -> LT.pack s

enumConstLine :: (String, Int) -> Text
enumConstLine (name, value) = let v = show value in [lt|    #{name} = #{v};|]

methodToProto :: Method -> Text
methodToProto Function{..} =
    let input = methodTypeToProto methodInput
        output = methodTypeToProto methodResult
    in [lt|    rpc #{methodName}(#{input}) returns (#{output});|]
methodToProto Event{..} =
    error $ "Protobuf: event method '" ++ methodName ++ "' has no protobuf equivalent"

methodTypeToProto :: MethodType -> Text
methodTypeToProto Void = "google.protobuf.Empty"
methodTypeToProto (Unary t) = LT.pack $ typeToProtoName t
methodTypeToProto (Streaming t) = LT.pack $ "stream " ++ typeToProtoName t

typeToProtoName :: Type -> String
typeToProtoName t = case protoScalarType t of
    Right s -> s
    Left err -> error $ "Protobuf: " ++ err
