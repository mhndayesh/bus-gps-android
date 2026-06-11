package com.busgps.android.ui.superadmin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemParentSuperBinding
import com.busgps.android.model.Parent

class SuperParentAdapter(
    private val parents: List<Parent>,
    private val onEditCreds: (Parent) -> Unit
) : RecyclerView.Adapter<SuperParentAdapter.VH>() {

    inner class VH(val binding: ItemParentSuperBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemParentSuperBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = parents.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val parent = parents[position]
        holder.binding.apply {
            tvName.text = parent.name
            tvId.text = "ID: ${parent.id}"
            btnEditCreds.setOnClickListener { onEditCreds(parent) }
        }
    }
}
