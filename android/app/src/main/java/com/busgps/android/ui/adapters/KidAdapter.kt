package com.busgps.android.ui.adapters

import com.busgps.android.R
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemKidStatusBinding
import com.busgps.android.model.Kid

class KidAdapter(
    private val onTrack: (Kid) -> Unit
) : RecyclerView.Adapter<KidAdapter.VH>() {

    private val kids = mutableListOf<Kid>()

    fun submit(newKids: List<Kid>) {
        kids.clear()
        kids.addAll(newKids)
        notifyDataSetChanged()
    }

    inner class VH(val binding: ItemKidStatusBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemKidStatusBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = kids.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val kid = kids[position]
        holder.binding.apply {
            tvKidName.text = kid.name
            tvStatus.text = if (kid.onBus) root.context.getString(R.string.on_bus) else root.context.getString(R.string.at_home)
            tvBusPlate.text = kid.busPlate ?: "—"
            val color = if (kid.onBus) 0xFF4CAF50.toInt() else 0xFF9E9E9E.toInt()
            tvStatus.setTextColor(color)
            root.setOnClickListener { if (kid.onBus) onTrack(kid) }
        }
    }
}
