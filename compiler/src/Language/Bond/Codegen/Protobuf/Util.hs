-- Copyright (c) Microsoft. All rights reserved.
-- Licensed under the MIT license. See LICENSE file in the project root for full license information.

{-# LANGUAGE RecordWildCards #-}

module Language.Bond.Codegen.Protobuf.Util
    ( protoScalarType
    , protoFieldLine
    , validateDeclaration
    , needsEmptyImport
    , fieldsStartFromZero
    ) where

import Prelude
import Language.Bond.Syntax.Types
import Language.Bond.Syntax.Util hiding (isContainer)

protoScalarType :: Type -> Either String String
protoScalarType BT_Int8    = Right "int32"
protoScalarType BT_Int16   = Right "int32"
protoScalarType BT_Int32   = Right "int32"
protoScalarType BT_Int64   = Right "int64"
protoScalarType BT_UInt8   = Right "uint32"
protoScalarType BT_UInt16  = Right "uint32"
protoScalarType BT_UInt32  = Right "uint32"
protoScalarType BT_UInt64  = Right "uint64"
protoScalarType BT_Float   = Right "float"
protoScalarType BT_Double  = Right "double"
protoScalarType BT_Bool    = Right "bool"
protoScalarType BT_String  = Right "string"
protoScalarType BT_Blob    = Right "bytes"
protoScalarType (BT_UserDefined Struct{..} [])  = Right declName
protoScalarType (BT_UserDefined Enum{..} [])    = Right declName
protoScalarType (BT_UserDefined a@Alias{} args) = protoScalarType $ resolveAlias a args
protoScalarType BT_WString       = Left "wstring has no protobuf equivalent"
protoScalarType (BT_Set _)       = Left "set<T> has no protobuf equivalent"
protoScalarType (BT_Nullable _)  = Left "nullable<T> has no protobuf equivalent"
protoScalarType (BT_Bonded _)    = Left "bonded<T> has no protobuf equivalent"
protoScalarType BT_MetaName      = Left "bond_meta::name has no protobuf equivalent"
protoScalarType BT_MetaFullName  = Left "bond_meta::full_name has no protobuf equivalent"
protoScalarType (BT_TypeParam _) = Left "generic type parameters cannot be converted to protobuf"
protoScalarType (BT_IntTypeArg _) = Left "integer type arguments cannot be converted to protobuf"
protoScalarType (BT_UserDefined _ (_:_)) = Left "generic type instantiations cannot be converted to protobuf"
protoScalarType t = Left $ "unsupported type: " ++ show t

isContainer :: Type -> Bool
isContainer (BT_List _)   = True
isContainer (BT_Vector _) = True
isContainer (BT_Map _ _)  = True
isContainer (BT_Set _)    = True
isContainer _             = False

fieldsStartFromZero :: [Field] -> Bool
fieldsStartFromZero fs = any (\f -> fieldOrdinal f == 0) fs

protoFieldLine :: String -> Bool -> Field -> Either String String
protoFieldLine structName offsetByOne Field{..} = do
    let prefix = "Protobuf: field '" ++ fieldName ++ "' in struct '" ++ structName ++ "': "
    let protoOrdinal = if offsetByOne then fieldOrdinal + 1 else fieldOrdinal
    case fieldModifier of
        RequiredOptional -> Left $ prefix ++ "required_optional modifier not supported in protobuf"
        _ -> return ()
    validateDefault prefix fieldDefault
    case fieldType of
        BT_Maybe inner -> do
            t <- mapLeft prefix $ protoScalarType inner
            return $ "    optional " ++ t ++ " " ++ fieldName ++ " = " ++ show protoOrdinal ++ ";"
        BT_List element -> do
            checkNestedContainer prefix element
            t <- mapLeft prefix $ protoScalarType element
            return $ "    repeated " ++ t ++ " " ++ fieldName ++ " = " ++ show protoOrdinal ++ ";"
        BT_Vector element -> do
            checkNestedContainer prefix element
            t <- mapLeft prefix $ protoScalarType element
            return $ "    repeated " ++ t ++ " " ++ fieldName ++ " = " ++ show protoOrdinal ++ ";"
        BT_Map key value -> do
            checkNestedContainer prefix value
            k <- mapLeft prefix $ protoScalarType key
            v <- mapLeft prefix $ protoScalarType value
            return $ "    map<" ++ k ++ ", " ++ v ++ "> " ++ fieldName ++ " = " ++ show protoOrdinal ++ ";"
        other -> do
            t <- mapLeft prefix $ protoScalarType other
            return $ "    " ++ t ++ " " ++ fieldName ++ " = " ++ show protoOrdinal ++ ";"
  where
    mapLeft p (Left e) = Left (p ++ e)
    mapLeft _ (Right v) = Right v
    checkNestedContainer p element
        | isContainer element = Left $ p ++ "nested containers not supported in proto3"
        | otherwise = Right ()
    validateDefault _ Nothing = Right ()
    validateDefault _ (Just (DefaultInteger 0)) = Right ()
    validateDefault _ (Just (DefaultFloat 0.0)) = Right ()
    validateDefault _ (Just (DefaultBool False)) = Right ()
    validateDefault _ (Just (DefaultString "")) = Right ()
    validateDefault _ (Just DefaultNothing) = Right ()
    validateDefault _ (Just (DefaultEnum _)) = Right ()
    validateDefault p (Just _) = Left $ p ++ "non-default default values not supported in proto3"

validateDeclaration :: Declaration -> Either String ()
validateDeclaration Alias{..} =
    Left $ "Protobuf: type alias '" ++ declName ++ "' cannot be converted to protobuf"
validateDeclaration Struct{..}
    | not (null declParams) = Left $ "Protobuf: generic struct '" ++ declName ++ "' cannot be converted to protobuf"
    | otherwise = Right ()
validateDeclaration Enum{..} = Right ()
validateDeclaration Forward{..} = Right ()
validateDeclaration Service{..}
    | not (null declParams) = Left $ "Protobuf: generic service '" ++ declName ++ "' cannot be converted to protobuf"
    | otherwise = Right ()

needsEmptyImport :: [Declaration] -> Bool
needsEmptyImport = any checkDecl
  where
    checkDecl Service{..} = any checkMethod serviceMethods
    checkDecl _ = False
    checkMethod Function{..} = isVoid methodResult || isVoid methodInput
    checkMethod Event{..} = True
    isVoid Void = True
    isVoid _ = False
