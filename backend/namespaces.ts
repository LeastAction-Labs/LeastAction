/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Namespace, SubjectSet, Context } from "@ory/keto-namespace-types" 

class User implements Namespace {} 

class Group implements Namespace { 
    related : { 
        owners : User[] , 
        editors : User[] , 
        viewers : User[]   
    }
    permits = {
        view : ( ctx : Context ) : boolean => 
            this.related.owners.includes(ctx.subject) ||
            this.related.editors.includes(ctx.subject) || 
            this.related.viewers.includes(ctx.subject) , 
        edit : ( ctx : Context ) : boolean => 
            this.related.editors.includes(ctx.subject) || 
            this.related.owners.includes(ctx.subject) ,
    }  
}

class Item implements Namespace { 
    related : { 
        owners : ( User | SubjectSet<Group,"owners"> | SubjectSet<Group,"editors"> | SubjectSet<Group,"viewers"> ) [] , 
        viewers : ( User | SubjectSet<Group,"owners"> | SubjectSet<Group,"editors"> | SubjectSet<Group,"viewers"> ) [] , 
        editors : ( User | SubjectSet<Group,"owners"> | SubjectSet<Group,"editors"> | SubjectSet<Group,"viewers"> ) [] , 
        true_parent : Item[] , 
        false_parents : Item[]
    }  
    permits = {
        view : ( ctx : Context ) : boolean => 
            this.related.owners.includes(ctx.subject) ||
            this.related.editors.includes(ctx.subject) || 
            this.related.viewers.includes(ctx.subject) || 
            this.related.true_parent.traverse((parent)=>parent.permits.view(ctx))|| 
            this.related.false_parents.traverse((parent)=>parent.permits.view(ctx)),

        edit : ( ctx : Context ) : boolean => 
            this.related.editors.includes(ctx.subject) || 
            this.related.owners.includes(ctx.subject) ||
            this.related.true_parent.traverse((parent)=>parent.permits.edit(ctx)) ,

        true_parent_edit : ( ctx : Context ) : boolean =>
            this.related.true_parent.traverse((parent)=>parent.permits.edit(ctx)), 

        delete : ( ctx : Context ) : boolean => 
            this.permits.true_parent_edit(ctx) || 
            this.related.false_parents.traverse((parent)=>parent.permits.edit(ctx)), 

        own : (ctx : Context ) : boolean => 
            this.related.owners.includes(ctx.subject) || 
            this.related.true_parent.traverse((parent)=>parent.permits.own(ctx)) , 
        
        is_true_parent : (ctx : Context) : boolean => 
            this.related.true_parent.includes(ctx.subject) || 
            this.related.true_parent.traverse((parent)=>parent.permits.is_true_parent(ctx)) 
    }  
}